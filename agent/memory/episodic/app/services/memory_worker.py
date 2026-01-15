"""
Memory Worker Service

Background worker that processes memory write jobs from a queue.
This allows for decoupled, async memory processing.
"""

from typing import Dict, Any, Optional
import logging
import threading
import queue
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryWorker:
    """
    Background worker for processing memory write jobs.

    Consumes jobs from a queue and invokes memory_write_graph.
    Supports graceful shutdown and error handling.
    """

    def __init__(self, max_workers: int = 2):
        """
        Initialize the memory worker.

        Args:
            max_workers: Number of worker threads
        """
        self.job_queue: queue.Queue = queue.Queue()
        self.workers: list = []
        self.max_workers = max_workers
        self.running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the worker threads."""
        with self._lock:
            if self.running:
                logger.warning("MemoryWorker already running")
                return

            self.running = True

            for i in range(self.max_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"MemoryWorker-{i}",
                    daemon=True
                )
                worker.start()
                self.workers.append(worker)

            logger.info(f"Started MemoryWorker with {self.max_workers} workers")

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the worker threads gracefully.

        Args:
            timeout: Max seconds to wait for workers to finish
        """
        with self._lock:
            if not self.running:
                return

            self.running = False

            # Add sentinel values to unblock workers
            for _ in self.workers:
                self.job_queue.put(None)

            # Wait for workers to finish
            deadline = time.time() + timeout
            for worker in self.workers:
                remaining = max(0, deadline - time.time())
                worker.join(timeout=remaining)

            self.workers = []
            logger.info("MemoryWorker stopped")

    def enqueue(self, payload: Dict[str, Any]) -> bool:
        """
        Add a job to the processing queue.

        Args:
            payload: Memory write payload

        Returns:
            True if enqueued successfully
        """
        if not self.running:
            logger.warning("MemoryWorker not running, job dropped")
            return False

        try:
            self.job_queue.put(payload, block=False)
            return True
        except queue.Full:
            logger.error("Job queue full, dropping job")
            return False

    def _worker_loop(self) -> None:
        """Main worker loop - processes jobs from queue."""
        thread_name = threading.current_thread().name
        logger.debug(f"{thread_name} started")

        while self.running:
            try:
                # Get job with timeout to check running flag
                try:
                    job = self.job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Sentinel value means shutdown
                if job is None:
                    break

                # Process the job
                self._process_job(job)
                self.job_queue.task_done()

            except Exception as e:
                logger.error(f"{thread_name} error: {str(e)}")

        logger.debug(f"{thread_name} stopped")

    def _process_job(self, payload: Dict[str, Any]) -> None:
        """
        Process a single memory write job.

        Args:
            payload: Memory write payload
        """
        try:
            from app.graphs.memory_write_graph import run_memory_write_graph
            from app.graphs.memory_write_graph.state import MemoryWriteState

            user_id = payload.get("user_id")
            prompt = payload.get("prompt", "")
            llm_output = payload.get("llm_output", "")

            if not user_id or not prompt:
                logger.debug("Skipping job - missing user_id or prompt")
                return

            # Build initial state
            initial_state: MemoryWriteState = {
                "user_id": user_id,
                "prompt": prompt,
                "llm_output": str(llm_output) if llm_output else "",
                "task_type": payload.get("task_type"),
                "app": payload.get("app"),
                "entities": payload.get("entities", []),
                "memory_intents": payload.get("memory_intents"),
                "importance_score": payload.get("importance_score"),
                "conversation_id": payload.get("conversation_id"),
                "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
                "errors": []
            }

            # Run memory_write_graph
            result = run_memory_write_graph(initial_state)

            if result.get("completed"):
                logger.info(f"Job completed: user={user_id}, action={result.get('action')}")
            else:
                logger.warning(f"Job incomplete: {result.get('errors')}")

        except Exception as e:
            logger.error(f"Job processing error: {str(e)}")


# Global worker instance
_memory_worker: Optional[MemoryWorker] = None
_worker_lock = threading.Lock()


def get_memory_worker() -> MemoryWorker:
    """Get or create the global memory worker instance."""
    global _memory_worker

    with _worker_lock:
        if _memory_worker is None:
            from app.config import config
            max_workers = getattr(config, 'MEMORY_WORKER_THREADS', 2)
            _memory_worker = MemoryWorker(max_workers=max_workers)

        return _memory_worker


def start_memory_worker() -> MemoryWorker:
    """Start the global memory worker."""
    worker = get_memory_worker()
    worker.start()
    return worker


def stop_memory_worker() -> None:
    """Stop the global memory worker."""
    global _memory_worker

    with _worker_lock:
        if _memory_worker is not None:
            _memory_worker.stop()
            _memory_worker = None


if __name__ == "__main__":
    # Allow running as standalone service
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting MemoryWorker service...")
    worker = start_memory_worker()

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_memory_worker()
        sys.exit(0)
