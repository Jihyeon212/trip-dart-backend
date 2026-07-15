from app.schemas.location import Location
from app.schemas.trip import CandidateResponse, Coordinate
from app.services.location_service import location_service
from app.utils.distance import calculate_distance_km


RADIUS_STEPS = {
    "walking": [5.0, 7.5, 10.0],
    "public_transit": [10.0, 15.0, 20.0],
}

NO_CANDIDATES_MESSAGE = "현재 데이터에서 조건에 맞는 장소를 찾지 못했습니다."
FALLBACK_MESSAGE = "설정한 반경에 후보가 없어 광주 전체에서 조회했습니다."


def find_candidates(
    category: str,
    transport_mode: str,
    center: Coordinate | None = None,
    excluded_content_ids: list[str] | None = None,
) -> CandidateResponse:
    excluded_ids = {str(content_id) for content_id in (excluded_content_ids or [])}
    category_locations = location_service.get_locations_by_category(category)
    available_locations = [
        location
        for location in category_locations
        if location.contentid not in excluded_ids
    ]

    if center is None:
        locations = [
            location.model_copy(update={"distance_km": None})
            for location in available_locations
        ]
        return CandidateResponse(
            locations=locations,
            search_scope="all_gwangju",
            applied_radius_km=None,
            radius_expanded=False,
            candidate_count=len(locations),
            message=None if locations else NO_CANDIDATES_MESSAGE,
        )

    locations_with_distance: list[tuple[float, Location]] = []
    for location in available_locations:
        distance = calculate_distance_km(
            center.latitude,
            center.longitude,
            location.latitude,
            location.longitude,
        )
        response_location = location.model_copy(
            update={"distance_km": round(distance, 2)}
        )
        locations_with_distance.append((distance, response_location))

    locations_with_distance.sort(
        key=lambda item: (item[0], item[1].title, item[1].contentid)
    )

    radius_steps = RADIUS_STEPS[transport_mode]
    for index, radius in enumerate(radius_steps):
        locations_in_radius = [
            location
            for distance, location in locations_with_distance
            if distance <= radius
        ]
        if locations_in_radius:
            return CandidateResponse(
                locations=locations_in_radius,
                search_scope="radius",
                applied_radius_km=radius,
                radius_expanded=index > 0,
                candidate_count=len(locations_in_radius),
                message=None,
            )

    fallback_locations = [location for _, location in locations_with_distance]
    return CandidateResponse(
        locations=fallback_locations,
        search_scope="all_gwangju",
        applied_radius_km=None,
        radius_expanded=True,
        candidate_count=len(fallback_locations),
        message=FALLBACK_MESSAGE if fallback_locations else NO_CANDIDATES_MESSAGE,
    )
