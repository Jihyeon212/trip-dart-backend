from pydantic import BaseModel


class LocationBase(BaseModel):
    name: str
    category: str
    latitude: float
    longitude: float


class LocationResponse(LocationBase):
    id: int
