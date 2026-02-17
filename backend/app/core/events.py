"""
SSE Event Manager — broadcasts ticket events to connected clients.
Uses asyncio.Queue per client for fan-out.
"""
import asyncio
import json
from typing import Any


class EventManager:
    """Manages SSE client connections and broadcasts events."""

    def __init__(self):
        self._clients: list[asyncio.Queue] = []

    async def subscribe(self) -> asyncio.Queue:
        """Add a new client and return its queue."""
        q: asyncio.Queue = asyncio.Queue()
        self._clients.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a client queue."""
        if q in self._clients:
            self._clients.remove(q)

    def broadcast(self, event_type: str, data: Any = None):
        """Send an event to ALL connected clients (sync-safe)."""
        payload = json.dumps({"type": event_type, "data": data}, default=str)
        dead: list[asyncio.Queue] = []
        for q in self._clients:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._clients.remove(q)


# Singleton instance
event_manager = EventManager()
