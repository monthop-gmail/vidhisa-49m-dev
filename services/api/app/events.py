import asyncio
from typing import Set

# In-memory set of subscriber queues
_subscribers: Set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue):
    _subscribers.discard(q)


async def publish(event_type: str):
    """Broadcast event to all SSE subscribers."""
    for q in list(_subscribers):
        try:
            q.put_nowait(event_type)
        except asyncio.QueueFull:
            pass
