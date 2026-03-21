from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import records, stats, projection, leaderboard, feed, branch, branches, markers, organizations, sse


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app = FastAPI(title="Vidhisa 49M API", version="0.1.0")

app.add_middleware(NoCacheMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(records.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(projection.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(feed.router, prefix="/api")
app.include_router(branch.router, prefix="/api")
app.include_router(branches.router, prefix="/api")
app.include_router(markers.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(sse.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
