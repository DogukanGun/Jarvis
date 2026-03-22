"""
Real-time memory system monitoring server.

Provides a FastAPI backend that:
- Receives events from LangGraph nodes via MemoryMonitor.emit()
- Maintains live memory system state (graphs, episodes, promotions, services)
- Pushes events to browser clients via Server-Sent Events (SSE)
- Serves REST endpoints for episodes, proposals, and statistics
- Persists state to monitor_state.json

The server runs in a background daemon thread so it never blocks the memory pipeline.

Usage from graph nodes:

    monitor = get_monitor()
    monitor.emit("node_start", {"graph": "memory_write", "node": "fingerprint"})
    ...
    monitor.emit("episode_inserted", {"episode_id": "abc", "user_id": "u1"})
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MONITOR_STATE_DIR = Path(__file__).parent.parent
MONITOR_STATE_PATH = MONITOR_STATE_DIR / "monitor_state.json"


def _now_iso() -> str:
    """Return an ISO-8601 timestamp in UTC with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _now_ms() -> float:
    """Return current time in milliseconds."""
    return time.time() * 1000


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------

def _create_app(monitor: "MemoryMonitor") -> FastAPI:
    """Build and return the FastAPI application wired to *monitor*."""

    app = FastAPI(
        title="Memory System Monitor",
        description="Real-time monitoring API for the Jarvis episodic memory system.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3001",
            "http://127.0.0.1:3001",
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
        """Server-Sent Events stream for real-time monitoring."""
        queue: asyncio.Queue[dict] = asyncio.Queue()
        monitor.sse_queues.append(queue)

        async def _event_generator():
            try:
                # Replay existing events for newly-connected clients
                for past_event in list(monitor.events):
                    yield f"data: {json.dumps(past_event)}\n\n"

                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15.0)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
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
                "X-Accel-Buffering": "no",
            },
        )

    # -- REST endpoints -----------------------------------------------------

    @app.get("/api/state")
    async def get_state():
        """Return the current memory system state snapshot."""
        return monitor.state

    @app.get("/api/events/history")
    async def get_events_history():
        """Return all recorded events as a JSON array."""
        return monitor.events

    @app.get("/api/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "timestamp": _now_iso(), "backend": "memory_monitor"}

    @app.get("/api/episodes")
    async def list_episodes(
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        user_id: Optional[str] = None,
    ):
        """Browse episodes from SQLite storage."""
        try:
            from app.storage import get_episode_repository
            repo = get_episode_repository()
            episodes = repo.get_recent_episodes(
                user_id=user_id or "default",
                days=365,
                limit=limit,
            )
            return {
                "episodes": [ep.model_dump() for ep in episodes],
                "count": len(episodes),
                "offset": offset,
            }
        except Exception as e:
            return {"episodes": [], "count": 0, "error": str(e)}

    @app.get("/api/episodes/{episode_id}")
    async def get_episode(episode_id: str):
        """Get a single episode by ID."""
        try:
            from app.storage import get_episode_repository
            repo = get_episode_repository()
            episode = repo.get_episode_by_id(episode_id)
            if episode:
                return {"episode": episode.model_dump()}
            return {"error": "Episode not found"}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/query")
    async def query_memory(request: Request):
        """
        Run the memory MainGraph for a user query.
        Used by the router agent to retrieve context and persist exchanges.
        """
        try:
            body = await request.json()
            user_id = body.get("user_id", "default")
            prompt = body.get("prompt", "")
            context = body.get("context", {})

            from app.graphs.main_graph import run_main_graph
            result = run_main_graph(
                user_id=user_id,
                prompt=prompt,
                context=context,
            )

            return {
                "llm_output": result.get("llm_output", ""),
                "episodes": result.get("retrieved_episodes", []),
                "response_payload": result.get("response_payload", {}),
            }
        except Exception as e:
            return {"episodes": [], "error": str(e)}

    @app.get("/api/proposals")
    async def list_proposals():
        """List recent promotion proposals."""
        try:
            from app.storage import get_episode_repository
            repo = get_episode_repository()
            proposals = repo.get_recent_proposals(limit=50)
            return {
                "proposals": [p.model_dump() for p in proposals],
                "count": len(proposals),
            }
        except Exception as e:
            return {"proposals": [], "count": 0, "error": str(e)}

    @app.get("/api/stats")
    async def get_stats():
        """Computed statistics about the memory system."""
        stats = {
            "metrics": monitor.state.get("metrics", {}),
            "graphs": monitor.state.get("graphs", {}),
            "services": monitor.state.get("services", {}),
            "storage": monitor.state.get("storage", {}),
            "event_count": len(monitor.events),
            "timestamp": _now_iso(),
        }

        # Try to get live SQLite stats
        try:
            from app.storage import get_episode_repository
            repo = get_episode_repository()
            db_path = Path(repo.db_path)
            stats["storage"]["sqlite"] = {
                "episode_count": repo.count_episodes(),
                "db_size_bytes": db_path.stat().st_size if db_path.exists() else 0,
            }
        except Exception:
            pass

        # Try to check long-term memory health
        try:
            from app.clients.long_term_client import get_long_term_client
            lt_client = get_long_term_client()
            stats["storage"]["long_term"] = {
                "healthy": lt_client.health_check(),
                "backend": lt_client.backend,
            }
        except Exception:
            pass

        return stats

    @app.post("/api/reflection/trigger")
    async def trigger_reflection():
        """Manually trigger a reflection graph run."""
        monitor.emit("reflection_triggered", {"source": "manual"})
        return {"status": "triggered", "timestamp": _now_iso()}

    @app.post("/api/events/push")
    async def push_event(request: Request):
        """Receive an event from an external process."""
        event = await request.json()
        event_type = event.get("type", "")
        data = {k: v for k, v in event.items() if k not in ("type", "timestamp")}
        monitor.events.append(event)
        monitor._update_state(event_type, data)
        monitor._push_to_clients(event)
        monitor.save_state()
        return {"ok": True}

    @app.get("/api/search/events")
    async def search_events(q: str = ""):
        """Full-text search through memory events."""
        if not q:
            return {"results": [], "query": q}
        q_lower = q.lower()
        results = [
            evt for evt in monitor.events
            if q_lower in json.dumps(evt, default=str).lower()
        ]
        return {"results": results, "query": q, "count": len(results)}

    return app


# ---------------------------------------------------------------------------
# MemoryMonitor
# ---------------------------------------------------------------------------

class MemoryMonitor:
    """Central monitoring hub for the memory system.

    Call ``emit()`` from synchronous graph node code to record events,
    update state, push to SSE clients, and persist to disk.
    """

    def __init__(self, port: int = 8686):
        self.port = port
        self.events: list[dict] = []
        self.state: dict[str, Any] = {
            "status": "idle",
            "graphs": {
                "main_graph": {"runs": 0, "errors": 0, "last_run": None, "active_node": None},
                "memory_write_graph": {"runs": 0, "errors": 0, "last_run": None, "active_node": None},
                "reflection_graph": {"runs": 0, "errors": 0, "last_run": None, "active_node": None},
                "user_approval_graph": {"runs": 0, "errors": 0, "last_run": None, "active_node": None},
            },
            "metrics": {
                "total_episodes": 0,
                "total_promotions": 0,
                "total_rejections": 0,
                "total_reflections": 0,
                "total_searches": 0,
                "avg_write_latency_ms": 0,
                "avg_search_latency_ms": 0,
                "dedup_hit_count": 0,
                "dedup_total_count": 0,
                "secrets_redacted": 0,
            },
            "services": {
                "memory_worker": {"status": "stopped", "queue_depth": 0, "jobs_completed": 0},
                "approval_consumer": {"status": "stopped", "pending": 0},
                "reflection_scheduler": {"status": "stopped", "last_reflection": None, "next_reflection": None},
            },
            "storage": {
                "sqlite": {"episode_count": 0, "db_size_bytes": 0},
                "long_term": {"healthy": False, "backend": "unknown"},
            },
        }
        self.sse_queues: list[asyncio.Queue] = []

        self._app: FastAPI | None = None
        self._server_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._remote_mode: bool = False

        # Latency tracking for averages
        self._write_latencies: list[float] = []
        self._search_latencies: list[float] = []

    # -- Public API ---------------------------------------------------------

    def emit(self, event_type: str, data: dict | None = None) -> None:
        """Record an event, update state, push to SSE clients, and save.

        Synchronous and safe to call from any thread.
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
        self._update_state(event_type, data)
        self._push_to_clients(event)
        self.save_state()

    def _emit_remote(self, event: dict) -> None:
        """POST an event to a standalone monitor server."""
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
            pass

    async def start(self) -> None:
        """Start the FastAPI/uvicorn server in a background daemon thread."""
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
            loop.call_soon(ready.set)
            loop.run_until_complete(server.serve())

        self._server_thread = threading.Thread(
            target=_run_server,
            name="memory-monitor-server",
            daemon=True,
        )
        self._server_thread.start()

        ready.wait(timeout=5.0)
        await asyncio.sleep(0.3)

        logger.info("Memory monitor listening on http://localhost:%d", self.port)
        print(f"[memory-monitor] Listening on http://localhost:{self.port}")

    def save_state(self) -> None:
        """Write current state and events to monitor_state.json."""
        MONITOR_STATE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "state": self.state,
            "events": self.events[-500:],  # Keep last 500 events
            "saved_at": _now_iso(),
        }
        try:
            MONITOR_STATE_PATH.write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Failed to save monitor state: %s", exc)

    # -- State machine ------------------------------------------------------

    def _update_state(self, event_type: str, data: dict) -> None:
        """Apply state-machine transitions based on event type."""

        graph_name = data.get("graph")
        node_name = data.get("node")

        # Graph-level events
        if event_type == "graph_run_start":
            self.state["status"] = "active"
            if graph_name and graph_name in self.state["graphs"]:
                g = self.state["graphs"][graph_name]
                g["runs"] += 1
                g["last_run"] = _now_iso()
                g["active_node"] = None

        elif event_type == "graph_run_end":
            if graph_name and graph_name in self.state["graphs"]:
                g = self.state["graphs"][graph_name]
                g["active_node"] = None
            # Check if any graph is still active
            if not any(
                g["active_node"] is not None
                for g in self.state["graphs"].values()
            ):
                self.state["status"] = "idle"

        elif event_type == "graph_run_error":
            if graph_name and graph_name in self.state["graphs"]:
                g = self.state["graphs"][graph_name]
                g["errors"] += 1
                g["active_node"] = None
            self.state["status"] = "idle"

        # Node-level events
        elif event_type == "node_start":
            if graph_name and graph_name in self.state["graphs"]:
                self.state["graphs"][graph_name]["active_node"] = node_name

        elif event_type == "node_end":
            if graph_name and graph_name in self.state["graphs"]:
                self.state["graphs"][graph_name]["active_node"] = None

        elif event_type == "node_error":
            if graph_name and graph_name in self.state["graphs"]:
                self.state["graphs"][graph_name]["active_node"] = None

        # Episode events
        elif event_type == "episode_inserted":
            self.state["metrics"]["total_episodes"] += 1

        elif event_type == "episode_reinforced":
            pass  # Count tracked in metrics

        elif event_type == "episode_deduplicated":
            self.state["metrics"]["dedup_hit_count"] += 1
            self.state["metrics"]["dedup_total_count"] += 1

        # Promotion events
        elif event_type == "promotion_proposed":
            pass

        elif event_type == "promotion_approved":
            self.state["metrics"]["total_promotions"] += 1

        elif event_type == "promotion_rejected":
            self.state["metrics"]["total_rejections"] += 1

        elif event_type == "promotion_timeout":
            self.state["metrics"]["total_rejections"] += 1

        # Reflection events
        elif event_type == "reflection_start":
            self.state["metrics"]["total_reflections"] += 1

        # Search events
        elif event_type == "search_executed":
            self.state["metrics"]["total_searches"] += 1
            latency = data.get("latency_ms")
            if latency:
                self._search_latencies.append(latency)
                if len(self._search_latencies) > 100:
                    self._search_latencies = self._search_latencies[-100:]
                self.state["metrics"]["avg_search_latency_ms"] = round(
                    sum(self._search_latencies) / len(self._search_latencies), 1
                )

        # Secret redaction
        elif event_type == "secret_redacted":
            self.state["metrics"]["secrets_redacted"] += 1

        # Service status
        elif event_type == "service_status_change":
            service = data.get("service")
            if service and service in self.state["services"]:
                for key in ("status", "queue_depth", "pending", "jobs_completed",
                            "last_reflection", "next_reflection"):
                    if key in data:
                        self.state["services"][service][key] = data[key]

        # Write latency tracking
        elif event_type == "write_completed":
            latency = data.get("latency_ms")
            if latency:
                self._write_latencies.append(latency)
                if len(self._write_latencies) > 100:
                    self._write_latencies = self._write_latencies[-100:]
                self.state["metrics"]["avg_write_latency_ms"] = round(
                    sum(self._write_latencies) / len(self._write_latencies), 1
                )

    def _push_to_clients(self, event: dict) -> None:
        """Enqueue event for every connected SSE client.

        Safe to call from any thread.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            return

        for queue in list(self.sse_queues):
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except (RuntimeError, asyncio.QueueFull):
                pass


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_monitor: Optional[MemoryMonitor] = None
_monitor_lock = threading.Lock()


def get_monitor(port: int = 8686) -> MemoryMonitor:
    """Get or create the global MemoryMonitor singleton.

    The monitor is created lazily on first access. It does NOT
    auto-start the server — call ``await monitor.start()`` explicitly.
    """
    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = MemoryMonitor(port=port)
    return _monitor
