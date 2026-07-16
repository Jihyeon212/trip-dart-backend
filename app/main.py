from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI

from app.db.database import init_db
from app.routers import chat, health, locations, posts, reports, trips
from app.services.location_service import location_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    location_service.load_locations()
    yield


app = FastAPI(title="Trip Dart Backend", lifespan=lifespan, version="1.0.0")

app.include_router(health.router)
app.include_router(posts.router)
app.include_router(locations.router, prefix="/locations", tags=["locations"])
app.include_router(trips.router)
app.include_router(chat.router)
app.include_router(reports.router)


@app.get("/")
def read_root():
    return {"message": "Trip Dart Backend is running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
