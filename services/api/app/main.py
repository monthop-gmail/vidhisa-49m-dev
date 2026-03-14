from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import records, stats, projection, leaderboard, feed, branch

app = FastAPI(title="Vithisa 49M API", version="0.1.0")

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


@app.get("/api/health")
async def health():
    return {"status": "ok"}
