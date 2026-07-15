from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PostType = Literal["random_course", "travel_review", "local_info"]


class PostCreate(BaseModel):
    post_type: PostType
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=3000)
    nickname: str = Field(min_length=1, max_length=20)
    password: str = Field(pattern=r"^\d{4}$")
    route_data: list[dict[str, Any]] | None = None

    @field_validator("title", "content", "nickname", mode="before")
    @classmethod
    def strip_and_validate_text(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            raise ValueError("공백만 입력할 수 없습니다.")
        return stripped


class PostUpdate(PostCreate):
    pass


class PasswordRequest(BaseModel):
    password: str = Field(pattern=r"^\d{4}$")


class PasswordVerificationResponse(BaseModel):
    valid: bool


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_type: PostType
    title: str
    content: str
    nickname: str
    route_data: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_type: PostType
    title: str
    nickname: str
    created_at: datetime


class PostListResponse(BaseModel):
    items: list[PostListItem]
    page: int
    size: int
    total: int
    total_pages: int
