"""
Reflection Scheduler Service

Runs the reflection_graph periodically to extract patterns
from recent episodes and create promotion proposals.
"""

from typing import Dict, Any, Optional, List, Callable
import logging
import threading
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ReflectionScheduler:
    """
    Scheduler for running reflection_graph periodically.

    Extracts patterns from recent episodic memories and
    creates promotion proposals for consistent behaviors.
    """

    def __init__(
        self,
        interval_hours: float = 6.0,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the reflection scheduler.

        Args:
            interval_hours: Hours between reflection runs
            on_complete: Optional callback when reflection completes
        """
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.on_complete = on_complete
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_run: Optional[datetime] = None

    def start(self) -> None:
        """Start the scheduler thread."""
        with self._lock:
            if self.running:
                logger.warning("ReflectionScheduler already running")
                return

            self.running = True
            self._thread = threading.Thread(
                target=self._schedule_loop,
                name="ReflectionScheduler",
                daemon=True
            )
            self._thread.start()
            logger.info(f"ReflectionScheduler started (interval: {self.interval_hours}h)")

            from app.monitor import get_monitor
            next_run = datetime.utcnow() + timedelta(seconds=min(60, self.interval_seconds / 10))
            get_monitor().emit("service_status_change", {
                "service": "reflection_scheduler",
                "status": "running",
                "next_reflection": next_run.isoformat(),
            })

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the scheduler gracefully.

        Args:
            timeout: Max seconds to wait for thread to finish
        """
        with self._lock:
            if not self.running:
                return

            self.running = False

            if self._thread:
                self._thread.join(timeout=timeout)
                self._thread = None

            logger.info("ReflectionScheduler stopped")

            from app.monitor import get_monitor
            get_monitor().emit("service_status_change", {
                "service": "reflection_scheduler",
                "status": "stopped",
            })

    def run_now(self, user_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Run reflection immediately for specified users or all users.

        Args:
            user_ids: Optional list of user IDs to process

        Returns:
            List of reflection results
        """
        return self._run_reflection(user_ids)

    def _schedule_loop(self) -> None:
        """Main scheduler loop - runs reflection at intervals."""
        logger.info("Scheduler loop started")

        # Initial delay - don't run immediately on startup
        initial_delay = min(60, self.interval_seconds / 10)
        time.sleep(initial_delay)

        while self.running:
            try:
                # Check if it's time to run
                now = datetime.utcnow()
                should_run = (
                    self._last_run is None or
                    (now - self._last_run).total_seconds() >= self.interval_seconds
                )

                if should_run:
                    logger.info("Running scheduled reflection...")
                    results = self._run_reflection()
                    self._last_run = now

                    logger.info(f"Reflection completed: {len(results)} users processed")

                    # Update monitor with next run time
                    from app.monitor import get_monitor
                    next_run = now + timedelta(seconds=self.interval_seconds)
                    get_monitor().emit("service_status_change", {
                        "service": "reflection_scheduler",
                        "status": "running",
                        "last_reflection": now.isoformat(),
                        "next_reflection": next_run.isoformat(),
                    })

                    # Call completion callback if set
                    if self.on_complete:
                        for result in results:
                            self.on_complete(result)

                # Sleep in small increments to allow graceful shutdown
                sleep_time = min(60, self.interval_seconds / 10)
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                time.sleep(60)  # Back off on error

    def _run_reflection(self, user_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Run reflection for users.

        Args:
            user_ids: Optional list of user IDs (None = all active users)

        Returns:
            List of reflection results
        """
        from app.graphs.reflection_graph import run_reflection
        from app.storage import get_episode_repository
        from app.config import config

        results = []

        try:
            # If no user_ids specified, get all users with recent activity
            if user_ids is None:
                repo = get_episode_repository()
                user_ids = repo.get_active_users(
                    days=config.REFLECTION_LOOKBACK_DAYS
                )

            if not user_ids:
                logger.debug("No active users for reflection")
                return results

            logger.info(f"Running reflection for {len(user_ids)} users")

            for user_id in user_ids:
                try:
                    result = run_reflection(
                        user_id=user_id,
                        lookback_days=config.REFLECTION_LOOKBACK_DAYS
                    )
                    results.append({
                        "user_id": user_id,
                        "proposals_count": result.get("proposals_count", 0),
                        "pattern_count": result.get("pattern_count", 0),
                        "errors": result.get("errors", [])
                    })

                    logger.info(
                        f"Reflection for {user_id}: "
                        f"{result.get('pattern_count', 0)} patterns, "
                        f"{result.get('proposals_count', 0)} proposals"
                    )

                except Exception as e:
                    logger.error(f"Reflection error for {user_id}: {str(e)}")
                    results.append({
                        "user_id": user_id,
                        "proposals_count": 0,
                        "pattern_count": 0,
                        "errors": [str(e)]
                    })

        except Exception as e:
            logger.error(f"Reflection run error: {str(e)}")

        return results


# Global scheduler instance
_reflection_scheduler: Optional[ReflectionScheduler] = None
_scheduler_lock = threading.Lock()


def get_reflection_scheduler() -> ReflectionScheduler:
    """Get or create the global reflection scheduler instance."""
    global _reflection_scheduler

    with _scheduler_lock:
        if _reflection_scheduler is None:
            from app.config import config
            _reflection_scheduler = ReflectionScheduler(
                interval_hours=config.REFLECTION_SCHEDULE_HOURS
            )

        return _reflection_scheduler


def start_reflection_scheduler(
    on_complete: Optional[Callable[[Dict[str, Any]], None]] = None
) -> ReflectionScheduler:
    """
    Start the global reflection scheduler.

    Args:
        on_complete: Optional callback when reflection completes

    Returns:
        The scheduler instance
    """
    global _reflection_scheduler

    with _scheduler_lock:
        if _reflection_scheduler is None:
            from app.config import config
            _reflection_scheduler = ReflectionScheduler(
                interval_hours=config.REFLECTION_SCHEDULE_HOURS,
                on_complete=on_complete
            )
        elif on_complete:
            _reflection_scheduler.on_complete = on_complete

        _reflection_scheduler.start()
        return _reflection_scheduler


def stop_reflection_scheduler() -> None:
    """Stop the global reflection scheduler."""
    global _reflection_scheduler

    with _scheduler_lock:
        if _reflection_scheduler is not None:
            _reflection_scheduler.stop()
            _reflection_scheduler = None


if __name__ == "__main__":
    # Allow running as standalone service
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    def on_reflection_complete(result: Dict[str, Any]) -> None:
        """Log reflection results."""
        logger.info(f"Reflection complete for {result.get('user_id')}: {result}")

    logger.info("Starting ReflectionScheduler service...")

    # For testing, use a shorter interval
    scheduler = ReflectionScheduler(
        interval_hours=0.1,  # 6 minutes for testing
        on_complete=on_reflection_complete
    )
    scheduler.start()

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.stop()
        sys.exit(0)
