from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.location import Location
from app.services.location_service import CATEGORY_CONFIG


TransportMode = Literal["walking", "public_transit"]
SearchScope = Literal["radius", "all_gwangju"]


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TripCandidateRequest(BaseModel):
    category: str
    transport_mode: TransportMode
    center: Coordinate | None = None
    excluded_content_ids: list[str] = Field(default_factory=list)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if value not in CATEGORY_CONFIG:
            raise ValueError("지원하지 않는 카테고리입니다.")
        return value

    @field_validator("excluded_content_ids", mode="before")
    @classmethod
    def replace_none_with_empty_list(cls, value: Any) -> Any:
        return [] if value is None else value


class CandidateResponse(BaseModel):
    locations: list[Location]
    search_scope: SearchScope
    applied_radius_km: float | None
    radius_expanded: bool
    candidate_count: int
    message: str | None = None


class RandomLocationResponse(BaseModel):
    status: Literal["selected", "skipped"]
    selected_location: Location | None
    search_scope: SearchScope
    applied_radius_km: float | None
    radius_expanded: bool
    candidate_count: int
    message: str
