"""In-process SSE event bus shared between the auto-runner and HTTP layer."""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Any, AsyncIterator, Deque, Dict


class EventBus:
    def __init__(self, history: int = 200) -> None:
        self._queues: list[asyncio.Queue[Dict[str, Any]]] = []
        self._history: Deque[Dict[str, Any]] = deque(maxlen=history)

    def publish(self, kind: str, payload: Dict[str, Any]) -> None:
        event = {"ts": time.time(), "kind": kind, **payload}
        self._history.append(event)
        for q in list(self._queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def history(self) -> list[Dict[str, Any]]:
        return list(self._history)

    async def stream(self) -> AsyncIterator[str]:
        q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=256)
        # Replay history first so a late-joining client sees recent decisions.
        for ev in list(self._history):
            yield f"data: {json.dumps(ev)}\n\n"
        self._queues.append(q)
        try:
            while True:
                ev = await q.get()
                yield f"data: {json.dumps(ev)}\n\n"
        finally:
            try:
                self._queues.remove(q)
            except ValueError:
                pass


bus = EventBus()
