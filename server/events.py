from __future__ import annotations

import asyncio
from typing import Any, Dict, List


class EventBus:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue):
        async with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    async def publish(self, event: Dict[str, Any]):
        async with self._lock:
            for q in list(self._subscribers):  # copy snapshot
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    # Drop if backpressure; could log
                    pass


event_bus = EventBus()
