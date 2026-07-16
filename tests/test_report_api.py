import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import reports


def request_body() -> dict:
    return {
        "region": "gwangju",
        "transport_mode": "walking",
        "visited_locations": [
            {
                "contentid": "123",
                "contenttypeid": "39",
                "title": "Lunch Spot",
                "category": "restaurant",
                "categoryLabel": "Restaurant",
                "address": "Gwangju",
                "tel": "062-000-0000",
                "longitude": 126.8526,
                "latitude": 35.1595,
                "image": "https://example.com/image.jpg",
                "copyrightType": "",
                "distanceKm": 1.2,
                "appliedRadiusKm": 3,
            },
            {
                "contentid": "456",
                "title": "Museum",
                "category": "cultural_facility",
                "categoryLabel": "Culture",
            },
        ],
        "inputs": {
            "locations": {
                "123": {
                    "visitTime": "13:30",
                    "rating": 5,
                    "review": "Lunch was good.",
                }
            },
            "overallRating": 5,
            "overallReview": "A pleasant Gwangju trip.",
            "additionalNotes": "I want to return.",
        },
    }


class ReportApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app = FastAPI()
        app.include_router(reports.router)
        cls.client = TestClient(app)

    def test_generate_report_returns_expected_alias_structure_without_openai_key(self) -> None:
        with patch("app.services.report_service.settings.openai_api_key", None):
            response = self.client.post("/api/reports/generate", json=request_body())

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data), {"title", "summary", "timeline", "overallReview"})
        self.assertNotIn("overall_review", data)
        self.assertEqual([item["place"] for item in data["timeline"]], ["Lunch Spot", "Museum"])
        self.assertEqual(data["timeline"][0]["time"], "13:30")
        self.assertEqual(data["timeline"][0]["rating"], 5)
        self.assertEqual(data["timeline"][1]["time"], "")
        self.assertIsNone(data["timeline"][1]["rating"])

    def test_openai_failure_still_returns_200(self) -> None:
        with patch("app.services.report_service.settings.openai_api_key", "test-key"), patch(
            "app.services.report_service.OpenAI",
            side_effect=RuntimeError("failure"),
        ):
            response = self.client.post("/api/reports/generate", json=request_body())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["timeline"][0]["place"], "Lunch Spot")

    def test_invalid_rating_and_empty_locations_return_422(self) -> None:
        invalid_rating = request_body()
        invalid_rating["inputs"]["locations"]["123"]["rating"] = 0
        self.assertEqual(
            self.client.post("/api/reports/generate", json=invalid_rating).status_code,
            422,
        )

        empty_locations = request_body()
        empty_locations["visited_locations"] = []
        self.assertEqual(
            self.client.post("/api/reports/generate", json=empty_locations).status_code,
            422,
        )


if __name__ == "__main__":
    unittest.main()
