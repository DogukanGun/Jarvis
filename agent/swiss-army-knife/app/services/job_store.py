import asyncio
import uuid
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JobStore:
    """In-memory store for tracking async jobs and confirmation state."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._confirmation_events: Dict[str, asyncio.Event] = {}

    def create_job(self, tool_name: str = "", metadata: Dict = None) -> str:
        """Create a new job, return job_id."""
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "pending",  # pending | waiting_confirmation | running | completed | failed
                "tool_name": tool_name,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
                "result": None,
                "error": None,
            }
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["result"] = result

    def fail_job(self, job_id: str, error: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["error"] = error

    def confirm_job(self, job_id: str):
        """Mark a job as confirmed (user approved HIGH/CRITICAL execution)."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "confirmed"
        # Signal the confirmation event if one exists
        if job_id in self._confirmation_events:
            self._confirmation_events[job_id].set()

    def create_confirmation_event(self, job_id: str) -> asyncio.Event:
        """Create an asyncio.Event for waiting on confirmation."""
        event = asyncio.Event()
        self._confirmation_events[job_id] = event
        return event

    def list_jobs(self, status: str = None) -> list:
        with self._lock:
            jobs = list(self._jobs.values())
            if status:
                jobs = [j for j in jobs if j["status"] == status]
            return jobs


# Singleton
job_store = JobStore()
