from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CurrentRouteLocation(BaseModel):
    contentid: str
    title: str
    category: str
    category_name: str | None = None
    addr1: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    current_route: list[CurrentRouteLocation] = Field(default_factory=list)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("메시지를 입력해주세요.")
        return stripped


class ChatLocation(BaseModel):
    contentid: str
    title: str
    category: str
    category_name: str
    addr1: str
    image_url: str
    thumbnail_url: str
    tel: str
    latitude: float
    longitude: float


class ChatPost(BaseModel):
    id: int
    post_type: str
    title: str
    content: str
    nickname: str
    created_at: datetime


class ChatResponse(BaseModel):
    answer: str
    locations: list[ChatLocation]
    posts: list[ChatPost]
