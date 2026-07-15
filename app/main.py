from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.db.database import init_db
from app.routers import chat, health, locations, posts, reports, trips


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Trip Dart Backend", lifespan=lifespan, version="1.0.0")

app.include_router(health.router)
app.include_router(posts.router, prefix="/posts", tags=["posts"])
app.include_router(locations.router, prefix="/locations", tags=["locations"])
app.include_router(trips.router, prefix="/trips", tags=["trips"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


@app.get("/")
def read_root():
    return {"message": "Trip Dart Backend is running"}
