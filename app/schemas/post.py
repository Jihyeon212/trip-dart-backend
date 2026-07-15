from datetime import datetime

from pydantic import BaseModel


class PostCreate(BaseModel):
    post_type: str
    title: str
    content: str
    nickname: str
    password: str
    route_data: list[dict] | None = None


class PostResponse(PostCreate):
    id: int
    created_at: datetime
    updated_at: datetime
