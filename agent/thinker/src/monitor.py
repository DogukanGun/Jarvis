"""
Real-time pipeline monitoring server.

Provides a FastAPI backend that:
- Receives events from the pipeline via PipelineMonitor.emit()
- Maintains live pipeline state (phases, problems, metrics)
- Pushes events to browser clients via Server-Sent Events (SSE)
- Serves REST endpoints for state, events, lessons, and metrics
- Persists state to outputs/monitor_state.json

The server runs in a background daemon thread so it never blocks the pipeline.

Usage from the pipeline orchestrator:

    monitor = PipelineMonitor(port=8585)
    await monitor.start()
    monitor.emit("pipeline_start", {"topic": "LLM efficiency"})
    ...
    monitor.emit("phase_start", {"problem_id": "p1", "phase": "gather"})
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUTS_DIR = Path("outputs")
STATE_PATH = OUTPUTS_DIR / "monitor_state.json"
LESSONS_PATH = OUTPUTS_DIR / "lessons_learned.json"
METRICS_PATH = OUTPUTS_DIR / "metrics_report.json"


class RunRequest(BaseModel):
    topic: str = "LLM efficiency and compression"
    agent: str = "claude"
    max_problems: int | None = None
    max_accepted: int | None = None
    max_research: int | None = None


def _read_json_file(path: Path) -> Any:
    """Read and parse a JSON file, returning None if it doesn't exist or is invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _now_iso() -> str:
    """Return an ISO-8601 timestamp in UTC with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------

def _create_app(monitor: "PipelineMonitor") -> FastAPI:
    """Build and return the FastAPI application wired to *monitor*."""

    app = FastAPI(
        title="Thinker Pipeline Monitor",
        description="Real-time monitoring API for the Problem-to-Paper pipeline.",
        version="1.0.0",
    )

    # Allow the Next.js dev server (and common variants) to connect.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- SSE endpoint -------------------------------------------------------

    @app.get("/api/events")
    async def sse_events(request: Request):
        """Server-Sent Events stream.

        Each connected client gets its own asyncio.Queue.  Events are pushed
        into all queues from ``PipelineMonitor.emit``.  The generator yields
        until the client disconnects.
        """
        queue: asyncio.Queue[dict] = asyncio.Queue()
        monitor.sse_queues.append(queue)

        async def _event_generator():
            try:
                # Replay existing events so newly-connected clients see history.
                for past_event in list(monitor.events):
                    yield f"data: {json.dumps(past_event)}\n\n"

                while True:
                    # Check for client disconnect between polls.
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15.0)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        # Send a keep-alive comment to prevent proxies/browsers
                        # from closing the connection.
                        yield ": keep-alive\n\n"
            finally:
                # Clean up when the client disconnects.
                try:
                    monitor.sse_queues.remove(queue)
                except ValueError:
                    pass

        return StreamingResponse(
            _event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # disable nginx buffering
            },
        )

    # -- REST endpoints -----------------------------------------------------

    @app.get("/api/state")
    async def get_state():
        """Return the current pipeline state snapshot."""
        return monitor.state

    @app.get("/api/events/history")
    async def get_events_history():
        """Return all recorded events as a JSON array."""
        return monitor.events

    @app.get("/api/lessons")
    async def get_lessons():
        """Return the contents of outputs/lessons_learned.json."""
        data = _read_json_file(LESSONS_PATH)
        if data is None:
            return {"lessons": [], "_note": "No lessons file found yet."}
        return data

    @app.get("/api/metrics")
    async def get_metrics():
        """Return the contents of outputs/metrics_report.json."""
        data = _read_json_file(METRICS_PATH)
        if data is None:
            return {"_note": "No metrics file found yet."}
        return data

    @app.post("/api/events/push")
    async def push_event(request: Request):
        """Receive an event from a pipeline subprocess running in remote mode."""
        event = await request.json()
        event_type = event.get("type", "")
        data = {k: v for k, v in event.items() if k not in ("type", "timestamp")}
        monitor.events.append(event)
        monitor._update_state(event_type, data)
        monitor._push_to_clients(event)
        monitor.save_state()
        return {"ok": True}

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "timestamp": _now_iso()}

    # -- Pipeline control endpoints ------------------------------------------

    @app.post("/api/pipeline/start")
    async def start_pipeline(req: RunRequest):
        """Start a new pipeline run as a subprocess."""
        if monitor._pipeline_proc is not None and monitor._pipeline_proc.poll() is None:
            return {"error": "Pipeline already running", "pid": monitor._pipeline_proc.pid}

        # Reset state for new run
        monitor.events.clear()
        monitor.state = {
            "status": "idle",
            "topic": req.topic,
            "start_time": None,
            "problems": {},
            "metrics": {"total_cost": 0.0, "total_tokens": 0, "total_duration_ms": 0},
            "healer_invocations": 0,
        }

        cmd = [
            sys.executable, "-m", "src.main",
            "--agent", req.agent,
            "--topic", req.topic,
        ]
        if req.max_problems is not None:
            cmd.extend(["--max-problems", str(req.max_problems)])
        if req.max_accepted is not None:
            cmd.extend(["--max-accepted", str(req.max_accepted)])
        if req.max_research is not None:
            cmd.extend(["--max-research", str(req.max_research)])

        # Add PATH for pdflatex
        import os
        env = os.environ.copy()
        env["PATH"] = f"/Library/TeX/texbin:{env.get('PATH', '')}"

        monitor._pipeline_proc = subprocess.Popen(
            cmd,
            cwd=str(Path.cwd()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

        # Stream stdout in a background thread
        def _stream_output():
            proc = monitor._pipeline_proc
            if proc and proc.stdout:
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        monitor.emit("agent_message", {"content": line, "source": "pipeline_stdout"})

        threading.Thread(target=_stream_output, daemon=True).start()

        return {"status": "started", "pid": monitor._pipeline_proc.pid, "topic": req.topic}

    @app.post("/api/pipeline/stop")
    async def stop_pipeline():
        """Stop the currently running pipeline."""
        if monitor._pipeline_proc is None or monitor._pipeline_proc.poll() is not None:
            return {"status": "not_running"}
        monitor._pipeline_proc.send_signal(signal.SIGTERM)
        monitor._pipeline_proc.wait(timeout=10)
        monitor.emit("pipeline_end", {"reason": "stopped_by_user"})
        return {"status": "stopped"}

    @app.get("/api/pipeline/status")
    async def pipeline_status():
        """Get the pipeline process status."""
        if monitor._pipeline_proc is None:
            return {"running": False, "pid": None}
        running = monitor._pipeline_proc.poll() is None
        return {"running": running, "pid": monitor._pipeline_proc.pid, "returncode": monitor._pipeline_proc.returncode}

    # -- Output exploration endpoints ----------------------------------------

    @app.get("/api/runs")
    async def list_runs():
        """List all problem output directories (past and current runs)."""
        runs = []
        if OUTPUTS_DIR.exists():
            for d in sorted(OUTPUTS_DIR.iterdir()):
                if d.is_dir() and not d.name.startswith(".") and d.name not in ("sub_agent_reports", "figures", "code", "execution_plans"):
                    files = [f.name for f in d.iterdir() if f.is_file()]
                    has_pdf = "paper_draft.pdf" in files
                    has_tex = "paper_draft.tex" in files
                    runs.append({
                        "problem_id": d.name,
                        "files": files,
                        "has_pdf": has_pdf,
                        "has_paper": has_tex,
                        "subdirs": [s.name for s in d.iterdir() if s.is_dir()],
                    })
        return {"runs": runs}

    @app.get("/api/outputs/{problem_id}")
    async def list_problem_outputs(problem_id: str):
        """List all output files for a specific problem."""
        problem_dir = OUTPUTS_DIR / problem_id
        if not problem_dir.exists():
            return {"error": f"Problem '{problem_id}' not found", "files": []}

        def _scan(directory: Path, prefix: str = "") -> list[dict]:
            items = []
            for item in sorted(directory.iterdir()):
                rel = f"{prefix}/{item.name}" if prefix else item.name
                if item.is_file():
                    items.append({
                        "name": rel,
                        "size": item.stat().st_size,
                        "type": "file",
                        "ext": item.suffix,
                    })
                elif item.is_dir():
                    items.append({"name": rel, "type": "dir"})
                    items.extend(_scan(item, rel))
            return items

        return {"problem_id": problem_id, "files": _scan(problem_dir)}

    @app.get("/api/outputs/{problem_id}/{file_path:path}")
    async def get_output_file(problem_id: str, file_path: str):
        """Read a specific output file's content."""
        from fastapi.responses import FileResponse, JSONResponse
        full_path = OUTPUTS_DIR / problem_id / file_path
        if not full_path.exists() or not full_path.is_file():
            return JSONResponse({"error": "File not found"}, status_code=404)

        # For binary files (PDF, PNG), serve as download
        if full_path.suffix in (".pdf", ".png", ".jpg", ".jpeg", ".gif"):
            return FileResponse(full_path, filename=full_path.name)

        # For text files, return content as JSON
        try:
            content = full_path.read_text(encoding="utf-8")
            if full_path.suffix == ".json":
                return {"file": file_path, "content": json.loads(content), "type": "json"}
            return {"file": file_path, "content": content, "type": "text"}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/api/search/events")
    async def search_events(q: str = ""):
        """Full-text search through all pipeline events."""
        if not q:
            return {"results": [], "query": q}
        q_lower = q.lower()
        results = []
        for evt in monitor.events:
            evt_str = json.dumps(evt, default=str).lower()
            if q_lower in evt_str:
                results.append(evt)
        return {"results": results, "query": q, "count": len(results)}

    @app.get("/api/search/outputs")
    async def search_outputs(q: str = ""):
        """Search through output file contents across all problems."""
        if not q:
            return {"results": [], "query": q}
        q_lower = q.lower()
        results = []
        if OUTPUTS_DIR.exists():
            for problem_dir in OUTPUTS_DIR.iterdir():
                if not problem_dir.is_dir():
                    continue
                for fpath in problem_dir.rglob("*"):
                    if not fpath.is_file() or fpath.suffix in (".pdf", ".png", ".jpg", ".db"):
                        continue
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        if q_lower in content.lower():
                            # Find matching lines
                            matches = []
                            for i, line in enumerate(content.split("\n"), 1):
                                if q_lower in line.lower():
                                    matches.append({"line": i, "text": line.strip()[:200]})
                                    if len(matches) >= 5:
                                        break
                            results.append({
                                "problem_id": problem_dir.name,
                                "file": str(fpath.relative_to(OUTPUTS_DIR)),
                                "matches": matches,
                            })
                    except Exception:
                        continue
        return {"results": results, "query": q, "count": len(results)}

    return app


# ---------------------------------------------------------------------------
# PipelineMonitor
# ---------------------------------------------------------------------------

class PipelineMonitor:
    """Central monitoring hub for the pipeline.

    Call ``emit()`` from synchronous pipeline code to record events, update
    state, push to SSE clients, and persist to disk.
    """

    def __init__(self, port: int = 8585):
        self.port = port
        self.events: list[dict] = []
        self.state: dict[str, Any] = {
            "status": "idle",           # idle | running | complete
            "topic": "",
            "start_time": None,
            "problems": {},             # problem_id -> {"phases": {"gather": "done", ...}}
            "metrics": {
                "total_cost": 0.0,
                "total_tokens": 0,
                "total_duration_ms": 0,
            },
            "healer_invocations": 0,
        }
        self.sse_queues: list[asyncio.Queue] = []

        self._app: FastAPI | None = None
        self._server_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pipeline_proc: subprocess.Popen | None = None
        self._remote_mode: bool = False

    # -- Public API ---------------------------------------------------------

    def emit(self, event_type: str, data: dict | None = None) -> None:
        """Record an event, update state, push to SSE clients, and save to disk.

        This method is **synchronous** and safe to call from the main pipeline
        thread.  It uses ``call_soon_threadsafe`` to enqueue SSE pushes on
        the server's event loop.

        In remote mode, POSTs the event to the standalone monitor server.
        """
        data = data or {}
        event: dict[str, Any] = {
            "type": event_type,
            "timestamp": _now_iso(),
            **data,
        }

        if self._remote_mode:
            self._emit_remote(event)
            return

        self.events.append(event)

        # --- state machine ---------------------------------------------------
        self._update_state(event_type, data)

        # --- push to SSE clients ---------------------------------------------
        self._push_to_clients(event)

        # --- persist ----------------------------------------------------------
        self.save_state()

    def _emit_remote(self, event: dict) -> None:
        """POST an event to the standalone monitor server."""
        import urllib.request
        try:
            req = urllib.request.Request(
                f"http://localhost:{self.port}/api/events/push",
                data=json.dumps(event).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # Non-blocking; don't crash pipeline if monitor is down

    async def start(self) -> None:
        """Start the FastAPI/uvicorn server in a background daemon thread.

        Returns immediately.  The server will be available at
        ``http://localhost:{self.port}``.
        """
        self._app = _create_app(self)

        ready = threading.Event()

        def _run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop

            config = uvicorn.Config(
                app=self._app,
                host="0.0.0.0",
                port=self.port,
                log_level="warning",
                loop="asyncio",
            )
            server = uvicorn.Server(config)

            # Signal the calling thread that the loop is ready.
            loop.call_soon(ready.set)
            loop.run_until_complete(server.serve())

        self._server_thread = threading.Thread(
            target=_run_server,
            name="monitor-server",
            daemon=True,
        )
        self._server_thread.start()

        # Wait (with timeout) for the background event loop to spin up.
        ready.wait(timeout=5.0)
        # Give uvicorn a moment to bind the port.
        await asyncio.sleep(0.3)

        logger.info("Pipeline monitor listening on http://localhost:%d", self.port)
        print(f"[monitor] Pipeline monitor listening on http://localhost:{self.port}")

    def save_state(self) -> None:
        """Write current state and events to ``outputs/monitor_state.json``."""
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "state": self.state,
            "events": self.events,
            "saved_at": _now_iso(),
        }
        try:
            STATE_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to save monitor state: %s", exc)

    # -- Internal helpers ---------------------------------------------------

    def _ensure_problem(self, problem_id: str) -> dict:
        """Return (or create) the state dict for *problem_id*."""
        if problem_id not in self.state["problems"]:
            self.state["problems"][problem_id] = {"phases": {}}
        return self.state["problems"][problem_id]

    def _update_state(self, event_type: str, data: dict) -> None:
        """Apply state-machine transitions based on the event type."""

        problem_id: str | None = data.get("problem_id")
        phase: str | None = data.get("phase")

        if event_type == "pipeline_start":
            self.state["status"] = "running"
            self.state["topic"] = data.get("topic", "")
            self.state["start_time"] = _now_iso()

        elif event_type == "pipeline_end":
            self.state["status"] = "complete"

        elif event_type == "phase_start":
            if problem_id and phase:
                prob = self._ensure_problem(problem_id)
                prob["phases"][phase] = "running"

        elif event_type == "phase_end":
            if problem_id and phase:
                prob = self._ensure_problem(problem_id)
                prob["phases"][phase] = "done"
            # Merge any metrics carried by the event.
            self._merge_metrics(data)

        elif event_type == "phase_error":
            if problem_id and phase:
                prob = self._ensure_problem(problem_id)
                prob["phases"][phase] = "error"

        elif event_type == "healer_start":
            if problem_id and phase:
                prob = self._ensure_problem(problem_id)
                prob["phases"][phase] = "healing"
            self.state["healer_invocations"] += 1

        elif event_type == "healer_end":
            if problem_id and phase:
                prob = self._ensure_problem(problem_id)
                prob["phases"][phase] = "healed"

        elif event_type == "agent_message":
            # No state mutation; the event is simply recorded.
            pass

    def _merge_metrics(self, data: dict) -> None:
        """Accumulate cost / token / duration metrics from an event payload."""
        m = self.state["metrics"]
        m["total_cost"] = round(m["total_cost"] + data.get("cost_usd", 0.0), 6)
        m["total_tokens"] += data.get("tokens", 0)
        m["total_duration_ms"] += data.get("duration_ms", 0)

    def _push_to_clients(self, event: dict) -> None:
        """Enqueue *event* for every connected SSE client.

        Safe to call from any thread.  If the server's event loop isn't
        running yet the push is silently skipped.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            return

        for queue in list(self.sse_queues):
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except (RuntimeError, asyncio.QueueFull):
                # Loop closed or queue full -- skip this client.
                pass
