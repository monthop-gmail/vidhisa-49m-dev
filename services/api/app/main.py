import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import async_session
from app.routers import (
    auth,
    branch,
    branches,
    enrollments,
    feed,
    ggs,
    leaderboard,
    markers,
    organizations,
    participants,
    projection,
    records,
    sse,
    stats,
)

log = logging.getLogger("vidhisa.autosync")
AUTO_SYNC_INTERVAL_SECONDS = int(os.getenv("AUTO_SYNC_INTERVAL_SECONDS", str(6 * 3600)))
AUTO_SYNC_ENABLED = os.getenv("AUTO_SYNC_ENABLED", "true").lower() in ("1", "true", "yes")


async def _auto_sync_loop() -> None:
    await asyncio.sleep(60)  # give app a minute to settle before first run
    while True:
        try:
            async with async_session() as db:
                result = await ggs.sync_all_record_ind(db, auto_approve=True)
            log.info("auto-sync ok: %s", {k: result[k] for k in ("branches", "created", "updated") if k in result})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("auto-sync failed: %s", exc)
        await asyncio.sleep(AUTO_SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_auto_sync_loop()) if AUTO_SYNC_ENABLED else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to prevent caching of API responses."""

    async def dispatch(self, request: Request, call_next):
        """Process request and add no-cache headers for API routes."""
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app = FastAPI(title="Vidhisa 49M API", version="0.1.0", lifespan=lifespan)

app.add_middleware(NoCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(enrollments.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(projection.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(feed.router, prefix="/api")
app.include_router(branch.router, prefix="/api")
app.include_router(branches.router, prefix="/api")
app.include_router(markers.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(participants.router, prefix="/api")
app.include_router(ggs.router, prefix="/api")
app.include_router(sse.router, prefix="/api")


@app.get("/api/healthz")
async def health():
    """Health check endpoint returning service status."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": app.version,
    }
