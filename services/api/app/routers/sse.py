"""Server-Sent Events (SSE) endpoint for real-time notifications."""

import asyncio

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from app.events import subscribe, unsubscribe

router = APIRouter()


@router.get("/sse")
async def sse_stream():
    """Stream real-time event notifications via SSE.

    Clients receive events for new records, approvals, and rejections.
    Sends keepalive comments every 30 seconds to maintain connection.
    """
    q = subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    event_type = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"event: {event_type}\ndata: {event_type}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                except (asyncio.CancelledError, GeneratorExit):
                    break
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
