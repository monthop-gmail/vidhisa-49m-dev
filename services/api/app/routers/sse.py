import asyncio
from fastapi import APIRouter
from starlette.responses import StreamingResponse
from app.events import subscribe, unsubscribe

router = APIRouter()


@router.get("/sse")
async def sse_stream():
    q = subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    event_type = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"event: {event_type}\ndata: {event_type}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment every 30s
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
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
