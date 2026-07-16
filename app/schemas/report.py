import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ReportBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class VisitedLocation(ReportBaseModel):
    contentid: str
    contenttypeid: str | None = None
    title: str
    category: str
    category_label: str | None = Field(default=None, alias="categoryLabel")
    address: str | None = None
    tel: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    image: str | None = None
    copyright_type: str | None = Field(default=None, alias="copyrightType")
    distance_km: float | None = Field(default=None, alias="distanceKm")
    applied_radius_km: float | None = Field(default=None, alias="appliedRadiusKm")

    @field_validator("contentid", mode="before")
    @classmethod
    def stringify_contentid(cls, value: Any) -> str:
        if value is None:
            raise ValueError("contentid is required")
        return str(value)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title must not be empty")
        return title


class LocationInput(ReportBaseModel):
    visit_time: str | None = Field(default=None, alias="visitTime")
    rating: int | None = Field(default=None, ge=1, le=5)
    review: str | None = Field(default=None, max_length=1000)

    @field_validator("visit_time")
    @classmethod
    def validate_visit_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if not TIME_PATTERN.match(stripped):
            raise ValueError("visitTime must be HH:MM")
        return stripped

    @field_validator("review")
    @classmethod
    def strip_review(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ReportInputs(ReportBaseModel):
    locations: dict[str, LocationInput] = Field(default_factory=dict)
    overall_rating: int | None = Field(default=None, alias="overallRating", ge=1, le=5)
    overall_review: str | None = Field(default=None, alias="overallReview", max_length=2000)
    additional_notes: str | None = Field(default=None, alias="additionalNotes", max_length=2000)

    @field_validator("locations", mode="before")
    @classmethod
    def default_locations(cls, value: Any) -> Any:
        return {} if value is None else value

    @field_validator("overall_review", "additional_notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ReportGenerateRequest(ReportBaseModel):
    region: Literal["gwangju"]
    transport_mode: Literal["walking", "public_transit"]
    visited_locations: list[VisitedLocation] = Field(min_length=1, max_length=20)
    inputs: ReportInputs

    @model_validator(mode="after")
    def reject_duplicate_contentids(self) -> "ReportGenerateRequest":
        contentids = [location.contentid for location in self.visited_locations]
        if len(contentids) != len(set(contentids)):
            raise ValueError("visited_locations contains duplicate contentid values")
        return self


class ReportTimelineItem(ReportBaseModel):
    time: str
    place: str
    rating: int | None = None
    description: str


class ReportGenerateResponse(ReportBaseModel):
    title: str
    summary: str
    timeline: list[ReportTimelineItem]
    overall_review: str = Field(alias="overallReview")


class AIReportResult(ReportBaseModel):
    title: str
    summary: str
    timeline_descriptions: list[str] = Field(alias="timelineDescriptions")
    overall_review: str = Field(alias="overallReview")

    @field_validator("title", "summary", "overall_review")
    @classmethod
    def reject_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("AI response text must not be empty")
        return stripped

    @field_validator("timeline_descriptions")
    @classmethod
    def reject_empty_descriptions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("timelineDescriptions must not contain empty text")
        return cleaned
