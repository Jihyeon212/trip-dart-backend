import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import trips
from app.schemas.location import Location
from app.schemas.trip import Coordinate
from app.services.trip_service import find_candidates


def make_location(
    contentid: str,
    category: str = "restaurant",
    latitude: float = 35.0,
    longitude: float = 126.0,
) -> Location:
    return Location(
        contentid=contentid,
        contenttypeid="39",
        category=category,
        category_name="category",
        title=f"location-{contentid}",
        addr1="",
        addr2="",
        tel="",
        longitude=longitude,
        latitude=latitude,
        image_url="",
        thumbnail_url="",
        sigungucode="",
    )


class CandidateServiceTest(unittest.TestCase):
    def test_first_location_and_exclusion(self) -> None:
        original = [make_location("1"), make_location("2")]
        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=original,
        ):
            result = find_candidates("restaurant", "walking", None, ["1"])

        self.assertEqual([item.contentid for item in result.locations], ["2"])
        self.assertEqual(result.search_scope, "all_gwangju")
        self.assertFalse(result.radius_expanded)
        self.assertIsNone(result.locations[0].distance_km)

    def test_walking_starts_at_five_km_without_mutating_source(self) -> None:
        original = make_location("1")
        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=[original],
        ), patch("app.services.trip_service.calculate_distance_km", return_value=4.999):
            result = find_candidates("restaurant", "walking", Coordinate(latitude=35, longitude=126))

        self.assertEqual(result.applied_radius_km, 5.0)
        self.assertFalse(result.radius_expanded)
        self.assertEqual(result.locations[0].distance_km, 5.0)
        self.assertIsNone(original.distance_km)

    def test_walking_expands_to_second_radius(self) -> None:
        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=[make_location("1")],
        ), patch("app.services.trip_service.calculate_distance_km", return_value=6.0):
            result = find_candidates("restaurant", "walking", Coordinate(latitude=35, longitude=126))
        self.assertEqual(result.applied_radius_km, 7.5)
        self.assertTrue(result.radius_expanded)

    def test_public_transit_starts_at_ten_km(self) -> None:
        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=[make_location("1")],
        ), patch("app.services.trip_service.calculate_distance_km", return_value=9.0):
            result = find_candidates("restaurant", "public_transit", Coordinate(latitude=35, longitude=126))
        self.assertEqual(result.applied_radius_km, 10.0)
        self.assertFalse(result.radius_expanded)

    def test_fallback_and_no_candidates(self) -> None:
        center = Coordinate(latitude=35, longitude=126)
        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=[make_location("1")],
        ), patch("app.services.trip_service.calculate_distance_km", return_value=30.0):
            fallback = find_candidates("restaurant", "walking", center)
        self.assertEqual(fallback.search_scope, "all_gwangju")
        self.assertTrue(fallback.radius_expanded)
        self.assertEqual(fallback.candidate_count, 1)

        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=[],
        ):
            empty = find_candidates("restaurant", "walking", center)
        self.assertEqual(empty.locations, [])
        self.assertEqual(empty.candidate_count, 0)


class TripApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app = FastAPI()
        app.include_router(trips.router)
        cls.client = TestClient(app)

    def test_candidates_and_random_location(self) -> None:
        locations = [make_location("1"), make_location("2")]
        request = {
            "category": "restaurant",
            "transport_mode": "walking",
            "center": None,
            "excluded_content_ids": ["1"],
        }
        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=locations,
        ):
            candidates = self.client.post("/api/trips/candidates", json=request)
            selected = self.client.post("/api/trips/random-location", json=request)

        self.assertEqual(candidates.status_code, 200)
        self.assertEqual([item["contentid"] for item in candidates.json()["locations"]], ["2"])
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json()["selected_location"]["contentid"], "2")

    def test_invalid_inputs_return_422(self) -> None:
        base = {"category": "restaurant", "transport_mode": "walking"}
        self.assertEqual(
            self.client.post("/api/trips/candidates", json=base | {"category": "invalid"}).status_code,
            422,
        )
        self.assertEqual(
            self.client.post("/api/trips/candidates", json=base | {"transport_mode": "car"}).status_code,
            422,
        )

    def test_no_candidates_is_skipped_and_null_exclusions_are_allowed(self) -> None:
        with patch(
            "app.services.trip_service.location_service.get_locations_by_category",
            return_value=[],
        ):
            response = self.client.post(
                "/api/trips/random-location",
                json={
                    "category": "restaurant",
                    "transport_mode": "walking",
                    "excluded_content_ids": None,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
