from pydantic import BaseModel


class Location(BaseModel):
    contentid: str
    contenttypeid: str
    category: str
    category_name: str
    title: str
    addr1: str
    addr2: str
    tel: str
    longitude: float
    latitude: float
    image_url: str
    thumbnail_url: str
    sigungucode: str
    distance_km: float | None = None
