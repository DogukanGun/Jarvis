import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List
from collections import deque

logger = logging.getLogger(__name__)


class ManagedSession:
    def __init__(self, job_id: str, tool_name: str, process: asyncio.subprocess.Process):
        self.job_id = job_id
        self.tool_name = tool_name
        self.process = process
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.status = "running"
        self.output_buffer: deque = deque(maxlen=10000)  # last 10k lines
        self._drain_task: Optional[asyncio.Task] = None

    @property
    def is_alive(self) -> bool:
        return self.process.returncode is None


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, ManagedSession] = {}

    async def start_session(self, tool_name: str, cmd: List[str], cwd: str = None, env: Dict = None) -> str:
        """Start a long-running process, return job_id."""
        job_id = str(uuid.uuid4())
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        session = ManagedSession(job_id=job_id, tool_name=tool_name, process=process)
        self._sessions[job_id] = session
        session._drain_task = asyncio.create_task(self._drain_output(session))
        logger.info(f"Started session {job_id} for {tool_name}, pid={process.pid}")
        return job_id

    async def _drain_output(self, session: ManagedSession):
        """Background task to read stdout into buffer."""
        try:
            while True:
                line = await session.process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                session.output_buffer.append(decoded)
        except Exception as e:
            logger.error(f"Drain error for {session.job_id}: {e}")
        finally:
            session.status = "stopped"

    async def send_command(self, job_id: str, command: str) -> Optional[str]:
        """Send input to a running session's stdin."""
        session = self._sessions.get(job_id)
        if not session or not session.is_alive:
            return None
        try:
            session.process.stdin.write((command + "\n").encode())
            await session.process.stdin.drain()
            # Wait briefly for output
            await asyncio.sleep(0.5)
            # Return recent output
            recent = list(session.output_buffer)[-20:]
            return "\n".join(recent)
        except Exception as e:
            return f"Error: {e}"

    async def get_output(self, job_id: str, since: int = 0) -> Optional[str]:
        """Get buffered output since line N."""
        session = self._sessions.get(job_id)
        if not session:
            return None
        lines = list(session.output_buffer)
        return "\n".join(lines[since:])

    async def stop_session(self, job_id: str) -> bool:
        """Gracefully terminate, then SIGKILL after timeout."""
        session = self._sessions.get(job_id)
        if not session:
            return False
        try:
            session.process.terminate()
            try:
                await asyncio.wait_for(session.process.wait(), timeout=10)
            except asyncio.TimeoutError:
                session.process.kill()
                await session.process.wait()
            session.status = "stopped"
            if session._drain_task:
                session._drain_task.cancel()
            return True
        except Exception as e:
            logger.error(f"Stop error for {job_id}: {e}")
            return False

    def list_sessions(self) -> List[Dict]:
        return [
            {
                "job_id": s.job_id,
                "tool_name": s.tool_name,
                "started_at": s.started_at,
                "status": s.status,
                "is_alive": s.is_alive,
                "output_lines": len(s.output_buffer),
            }
            for s in self._sessions.values()
        ]


# Singleton
session_manager = SessionManager()
