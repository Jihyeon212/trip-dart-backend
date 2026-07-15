from pydantic import BaseModel


class TripCreate(BaseModel):
    title: str
    description: str | None = None


class TripResponse(TripCreate):
    id: int
