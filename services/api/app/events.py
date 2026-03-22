"""Event broadcasting for Server-Sent Events (SSE) notifications."""

import asyncio

_subscribers: set[asyncio.Queue[str]] = set()


def subscribe() -> asyncio.Queue[str]:
    """Subscribe to event notifications.

    Returns:
        Queue that will receive event notifications.
    """
    q: asyncio.Queue[str] = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue[str]) -> None:
    """Unsubscribe from event notifications.

    Args:
        q: The queue to unsubscribe.
    """
    _subscribers.discard(q)


async def publish(event_type: str) -> None:
    """Broadcast event to all SSE subscribers.

    Args:
        event_type: The type of event to broadcast.
    """
    for q in list(_subscribers):
        try:
            q.put_nowait(event_type)
        except asyncio.QueueFull:
            pass
