"""Code Analyzer — FastAPI Server."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import config
from app.models import ExecuteRequest, ExecuteResponse, ToolListResponse
from app.tools.registry import ToolRegistry
from app.tools.code.index_repo import IndexRepoTool
from app.tools.code.query_code import QueryCodeTool
from app.tools.code.get_context import GetContextTool
from app.tools.code.get_impact import GetImpactTool
from app.tools.code.get_routes import GetRoutesTool
from app.tools.code.visualize_graph import VisualizeGraphTool

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ── D3.js visualization HTML ──────────────────────────────────────────────────

GRAPH_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Graph · {repo_id}</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#030508;
    background-image:radial-gradient(circle,rgba(74,222,128,.055) 1px,transparent 1px);
    background-size:28px 28px;
    font-family:'SF Mono','Fira Code',monospace;
    color:#e0e0e0;
    overflow:hidden;
    height:100vh;
    width:100vw;
  }}
  svg {{ width:100%; height:100%; }}

  /* nodes */
  .node circle {{
    stroke:rgba(0,0,0,.4);
    stroke-width:1px;
    cursor:pointer;
    transition:opacity .2s;
  }}
  .node text {{
    font-size:9px;
    fill:rgba(255,255,255,.65);
    pointer-events:none;
    text-anchor:middle;
    dominant-baseline:hanging;
  }}
  .node.dimmed circle {{ opacity:.12; }}
  .node.dimmed text {{ opacity:.05; }}

  /* edges */
  .link {{
    stroke-opacity:.55;
    transition:opacity .2s;
  }}
  .link.dimmed {{ stroke-opacity:.04; }}

  /* arrowhead markers */
  .arrow {{ fill:none; }}

  /* tooltip */
  #tooltip {{
    position:fixed;
    background:rgba(5,10,8,.92);
    border:1px solid rgba(74,222,128,.25);
    border-radius:2px;
    padding:8px 12px;
    font-size:11px;
    line-height:1.6;
    pointer-events:none;
    display:none;
    max-width:280px;
    z-index:100;
  }}
  #tooltip .tt-name {{ color:#4ade80; font-size:12px; margin-bottom:3px; }}
  #tooltip .tt-row {{ color:#aaa; }}
  #tooltip .tt-row span {{ color:#ddd; }}

  /* stats bar */
  #stats {{
    position:fixed;
    top:10px; left:12px;
    font-size:10px;
    letter-spacing:.1em;
    color:rgba(74,222,128,.5);
    pointer-events:none;
  }}

  /* legend */
  #legend {{
    position:fixed;
    top:10px; right:12px;
    background:rgba(5,10,8,.8);
    border:1px solid rgba(74,222,128,.12);
    border-radius:2px;
    padding:8px 10px;
    font-size:10px;
  }}
  .leg-row {{ display:flex; align-items:center; gap:6px; margin:3px 0; color:rgba(255,255,255,.6); }}
  .leg-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}

  /* loading */
  #loading {{
    position:fixed; inset:0;
    display:flex; align-items:center; justify-content:center;
    font-size:12px; letter-spacing:.15em;
    color:rgba(74,222,128,.5);
  }}
</style>
</head>
<body>
<div id="loading">FETCHING GRAPH…</div>
<div id="stats"></div>
<div id="legend">
  <div class="leg-row"><div class="leg-dot" style="background:#3b82f6"></div>File</div>
  <div class="leg-row"><div class="leg-dot" style="background:#4ade80"></div>Function</div>
  <div class="leg-row"><div class="leg-dot" style="background:#f59e0b"></div>Class</div>
  <div class="leg-row"><div class="leg-dot" style="background:#a78bfa"></div>Method</div>
  <div class="leg-row"><div class="leg-dot" style="background:#f87171"></div>Route</div>
</div>
<div id="tooltip"></div>
<svg id="graph"></svg>

<script>
const REPO_ID = "{repo_id}";
const NODE_COLOR = {{
  File:'#3b82f6', Function:'#4ade80', Class:'#f59e0b', Method:'#a78bfa', Route:'#f87171'
}};
const NODE_R = {{File:7,Function:5,Class:8,Method:5,Route:6}};
const EDGE_COLOR = {{
  CALLS:'#4ade80',IMPORTS:'#3b82f6',EXTENDS:'#f59e0b',
  CONTAINS:'rgba(255,255,255,.15)',HAS_METHOD:'rgba(167,139,250,.4)',
  HANDLES_ROUTE:'#f87171'
}};

fetch(`/api/repos/${{REPO_ID}}/graph`)
  .then(r => r.json())
  .then(data => {{
    document.getElementById('loading').style.display = 'none';
    render(data);
  }})
  .catch(e => {{
    document.getElementById('loading').textContent = 'ERROR: ' + e.message;
  }});

function render({{nodes, edges}}) {{
  // Deduplicate edges for clarity (keep unique from→to pairs per type)
  const seen = new Set();
  const links = edges.filter(e => {{
    const k = e.from + '|' + e.to + '|' + e.type;
    if (seen.has(k)) return false;
    seen.add(k); return true;
  }});

  // Index nodes
  const nodeById = Object.fromEntries(nodes.map(n => [n.id, n]));

  document.getElementById('stats').textContent =
    `${{nodes.length}} nodes · ${{links.length}} edges · ${{REPO_ID}}`;

  const W = window.innerWidth, H = window.innerHeight;
  const svg = d3.select('#graph');

  // Arrow markers per edge type
  const defs = svg.append('defs');
  Object.entries(EDGE_COLOR).forEach(([type, color]) => {{
    defs.append('marker')
      .attr('id','arrow-'+type)
      .attr('viewBox','0 -4 8 8')
      .attr('refX',14).attr('refY',0)
      .attr('markerWidth',6).attr('markerHeight',6)
      .attr('orient','auto')
      .append('path').attr('d','M0,-4L8,0L0,4').attr('fill',color).attr('opacity',.7);
  }});

  const g = svg.append('g');

  svg.call(d3.zoom().scaleExtent([.05,4]).on('zoom', e => g.attr('transform', e.transform)));

  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(90))
    .force('charge', d3.forceManyBody().strength(-220))
    .force('center', d3.forceCenter(W/2, H/2))
    .force('collide', d3.forceCollide(20));

  const link = g.append('g').selectAll('line')
    .data(links).join('line')
    .attr('class','link')
    .attr('stroke', d => EDGE_COLOR[d.type] || '#555')
    .attr('stroke-width', d => (d.confidence || 1) * 1.5)
    .attr('marker-end', d => `url(#arrow-${{d.type}})`);

  const node = g.append('g').selectAll('.node')
    .data(nodes).join('g').attr('class','node')
    .call(d3.drag()
      .on('start', (e,d) => {{ if(!e.active) sim.alphaTarget(.3).restart(); d.fx=d.x; d.fy=d.y; }})
      .on('drag',  (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
      .on('end',   (e,d) => {{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}));

  node.append('circle')
    .attr('r', d => NODE_R[d.type] || 5)
    .attr('fill', d => NODE_COLOR[d.type] || '#888');

  node.append('text')
    .attr('dy', d => (NODE_R[d.type]||5) + 4)
    .text(d => d.name ? (d.name.length > 18 ? d.name.slice(0,16)+'…' : d.name) : '');

  sim.on('tick', () => {{
    link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
        .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
  }});

  // Tooltip
  const tip = document.getElementById('tooltip');
  node
    .on('mouseover', (e, d) => {{
      tip.style.display = 'block';
      tip.innerHTML = `
        <div class="tt-name">${{d.name || d.id}}</div>
        <div class="tt-row">type <span>${{d.type}}</span></div>
        ${{d.file_path ? `<div class="tt-row">file <span>${{d.file_path}}</span></div>` : ''}}
        ${{d.start_line ? `<div class="tt-row">line <span>${{d.start_line}}</span></div>` : ''}}
      `;
    }})
    .on('mousemove', e => {{
      tip.style.left = (e.clientX+14)+'px';
      tip.style.top  = (e.clientY-10)+'px';
    }})
    .on('mouseout', () => {{ tip.style.display='none'; }});

  // Click highlight
  const linksByNode = {{}};
  links.forEach(l => {{
    (linksByNode[l.source.id||l.source] = linksByNode[l.source.id||l.source]||new Set()).add(l.target.id||l.target);
    (linksByNode[l.target.id||l.target] = linksByNode[l.target.id||l.target]||new Set()).add(l.source.id||l.source);
  }});

  node.on('click', (e, d) => {{
    e.stopPropagation();
    const neighbors = linksByNode[d.id] || new Set();
    node.classed('dimmed', n => n.id !== d.id && !neighbors.has(n.id));
    link.classed('dimmed', l => {{
      const s = l.source.id||l.source, t = l.target.id||l.target;
      return s !== d.id && t !== d.id;
    }});
  }});

  svg.on('click', () => {{
    node.classed('dimmed', false);
    link.classed('dimmed', false);
  }});
}}
</script>
</body>
</html>
"""


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    ToolRegistry.register(IndexRepoTool())
    ToolRegistry.register(QueryCodeTool())
    ToolRegistry.register(GetContextTool())
    ToolRegistry.register(GetImpactTool())
    ToolRegistry.register(GetRoutesTool())
    ToolRegistry.register(VisualizeGraphTool())
    logger.info("Registered %d code analysis tools.", len(ToolRegistry.list_tools()))
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Code Analyzer",
    description="Codebase knowledge graph agent for Jarvis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent": config.AGENT_ID, "tools": len(ToolRegistry.list_tools())}


@app.get("/api/tools", response_model=ToolListResponse)
async def list_tools():
    tools = [t.model_dump() for t in ToolRegistry.list_tools()]
    return ToolListResponse(tools=tools, total=len(tools))


@app.get("/api/repos/{repo_id}/graph")
async def get_graph(repo_id: str):
    """Return the full knowledge graph as JSON."""
    from app.core.analyzer import get_cached_graph
    graph = get_cached_graph(repo_id)
    if graph is None:
        raise HTTPException(404, f"Repo '{repo_id}' not indexed. Call index_repo first.")
    return JSONResponse(graph.to_dict())


@app.get("/api/repos/{repo_id}/visualize", response_class=HTMLResponse)
async def visualize(repo_id: str):
    """Serve the interactive D3.js graph visualization."""
    from app.core.analyzer import get_cached_graph
    if get_cached_graph(repo_id) is None:
        raise HTTPException(404, f"Repo '{repo_id}' not indexed.")
    return HTMLResponse(GRAPH_HTML.format(repo_id=repo_id))


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    from app.agent.runner import run_agent

    try:
        result = await run_agent(
            user_id=req.user_id,
            message=req.message,
            target_tools=req.target_tools,
            parameters=req.parameters,
            confirmed=req.confirmed,
        )
        return ExecuteResponse(
            response=result.get("response", ""),
            report=result.get("report", {}),
            tools_used=result.get("tools_used", []),
            findings=result.get("findings", []),
        )
    except Exception as e:
        logger.error("Execute error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
