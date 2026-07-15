import random

from fastapi import APIRouter

from app.schemas.trip import (
    CandidateResponse,
    RandomLocationResponse,
    TripCandidateRequest,
)
from app.services.trip_service import find_candidates


router = APIRouter(
    prefix="/api/trips",
    tags=["Trips"],
)


@router.post("/candidates", response_model=CandidateResponse)
def get_trip_candidates(payload: TripCandidateRequest) -> CandidateResponse:
    return find_candidates(
        category=payload.category,
        transport_mode=payload.transport_mode,
        center=payload.center,
        excluded_content_ids=payload.excluded_content_ids,
    )


@router.post("/random-location", response_model=RandomLocationResponse)
def get_random_location(payload: TripCandidateRequest) -> RandomLocationResponse:
    candidates = find_candidates(
        category=payload.category,
        transport_mode=payload.transport_mode,
        center=payload.center,
        excluded_content_ids=payload.excluded_content_ids,
    )

    if not candidates.locations:
        return RandomLocationResponse(
            status="skipped",
            selected_location=None,
            search_scope=candidates.search_scope,
            applied_radius_km=candidates.applied_radius_km,
            radius_expanded=candidates.radius_expanded,
            candidate_count=candidates.candidate_count,
            message=candidates.message or "현재 데이터에서 조건에 맞는 장소를 찾지 못했습니다.",
        )

    return RandomLocationResponse(
        status="selected",
        selected_location=random.choice(candidates.locations),
        search_scope=candidates.search_scope,
        applied_radius_km=candidates.applied_radius_km,
        radius_expanded=candidates.radius_expanded,
        candidate_count=candidates.candidate_count,
        message="장소가 선택되었습니다.",
    )
