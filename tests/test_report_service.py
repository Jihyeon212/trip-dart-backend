import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.schemas.report import ReportGenerateRequest
from app.services.report_service import (
    DEFAULT_TIMELINE_DESCRIPTION,
    ReportService,
)


def make_request() -> ReportGenerateRequest:
    return ReportGenerateRequest.model_validate(
        {
            "region": "gwangju",
            "transport_mode": "walking",
            "visited_locations": [
                {
                    "contentid": "1",
                    "contenttypeid": "39",
                    "title": "First Place",
                    "category": "restaurant",
                    "categoryLabel": "Restaurant",
                    "address": "Gwangju",
                    "distanceKm": 1.2,
                },
                {
                    "contentid": "2",
                    "title": "Second Place",
                    "category": "tourist_spot",
                    "categoryLabel": "Spot",
                },
            ],
            "inputs": {
                "locations": {
                    "1": {
                        "visitTime": "13:30",
                        "rating": 5,
                        "review": "Good lunch.",
                    },
                    "999": {
                        "visitTime": "22:00",
                        "rating": 1,
                        "review": "Should be ignored.",
                    },
                },
                "overallRating": 5,
                "overallReview": "A good day in Gwangju.",
                "additionalNotes": "Next time, I want to visit more places.",
            },
        }
    )


def ai_output() -> str:
    return (
        '{"title":"AI title","summary":"AI summary",'
        '"timelineDescriptions":["AI first","AI second"],'
        '"overallReview":"AI overall",'
        '"aiInsights":{'
        '"travelStyle":{"title":"Food focused","description":"This trip shows a food-focused tendency."},'
        '"keywords":["Food","Food","Gwangju","Extra"],'
        '"satisfactionPoints":['
        '{"title":"Lunch satisfaction","description":"The lunch review was positive.","evidence":["Good lunch."]},'
        '{"title":"Made up","description":"This should be removed.","evidence":["Friendly staff."]}'
        '],'
        '"disappointmentPoints":['
        '{"title":"No evidence","description":"This should be removed.","evidence":["Too crowded."]}'
        '],'
        '"nextTripSuggestion":{"summary":"Keep restaurant-centered categories.",'
        '"recommendedCategories":["restaurant","restaurant","unknown","shopping","tourist_spot","leisure_sports"]}'
        '}'
        '}'
    )


class ReportSchemaTest(unittest.TestCase):
    def test_camel_case_request_aliases_are_mapped(self) -> None:
        request = make_request()

        self.assertEqual(request.visited_locations[0].category_label, "Restaurant")
        self.assertEqual(request.visited_locations[0].distance_km, 1.2)
        self.assertEqual(request.inputs.locations["1"].visit_time, "13:30")
        self.assertEqual(request.inputs.overall_rating, 5)
        self.assertEqual(request.inputs.overall_review, "A good day in Gwangju.")

    def test_invalid_rating_time_empty_locations_and_duplicates_fail(self) -> None:
        invalid_rating = make_request().model_dump(by_alias=True)
        invalid_rating["inputs"]["locations"]["1"]["rating"] = 6
        with self.assertRaises(Exception):
            ReportGenerateRequest.model_validate(invalid_rating)

        invalid_time = make_request().model_dump(by_alias=True)
        invalid_time["inputs"]["locations"]["1"]["visitTime"] = "25:00"
        with self.assertRaises(Exception):
            ReportGenerateRequest.model_validate(invalid_time)

        empty_locations = make_request().model_dump(by_alias=True)
        empty_locations["visited_locations"] = []
        with self.assertRaises(Exception):
            ReportGenerateRequest.model_validate(empty_locations)

        duplicate = make_request().model_dump(by_alias=True)
        duplicate["visited_locations"][1]["contentid"] = "1"
        with self.assertRaises(Exception):
            ReportGenerateRequest.model_validate(duplicate)


class ReportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ReportService()

    def test_timeline_keeps_visited_location_order_and_links_by_contentid(self) -> None:
        result = self.service.build_fallback_report(make_request())

        self.assertEqual([item.place for item in result.timeline], ["First Place", "Second Place"])
        self.assertEqual(result.timeline[0].time, "13:30")
        self.assertEqual(result.timeline[0].rating, 5)
        self.assertEqual(result.timeline[0].description, "Good lunch.")
        self.assertEqual(result.timeline[1].time, "")
        self.assertIsNone(result.timeline[1].rating)
        self.assertEqual(result.timeline[1].description, DEFAULT_TIMELINE_DESCRIPTION)
        self.assertIsNone(result.ai_insights)
        self.assertNotIn("Should be ignored.", result.model_dump_json())

    def test_missing_openai_key_uses_fallback_with_null_insights(self) -> None:
        with patch("app.services.report_service.settings.openai_api_key", None):
            result = self.service.generate_report(make_request())

        self.assertEqual(result.title, "AI가 정리해준 광주의 하루")
        self.assertEqual(result.timeline[0].description, "Good lunch.")
        self.assertIsNone(result.ai_insights)

    def test_ai_success_changes_only_ai_owned_fields_and_sanitizes_insights(self) -> None:
        create = Mock(return_value=SimpleNamespace(output_text=ai_output()))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))

        with patch("app.services.report_service.settings.openai_api_key", "test-key"), patch(
            "app.services.report_service.OpenAI",
            return_value=client,
        ):
            result = self.service.generate_report(make_request())

        self.assertEqual(result.title, "AI title")
        self.assertEqual(result.summary, "AI summary")
        self.assertEqual(result.overall_review, "AI overall")
        self.assertEqual(
            [(item.time, item.place, item.rating, item.description) for item in result.timeline],
            [
                ("13:30", "First Place", 5, "AI first"),
                ("", "Second Place", None, "AI second"),
            ],
        )

        self.assertIsNotNone(result.ai_insights)
        assert result.ai_insights is not None
        self.assertEqual(result.ai_insights.keywords, ["Food", "Gwangju", "Extra"])
        self.assertEqual(len(result.ai_insights.satisfaction_points), 1)
        self.assertEqual(result.ai_insights.satisfaction_points[0].evidence, ["Good lunch."])
        self.assertEqual(result.ai_insights.disappointment_points, [])
        self.assertEqual(
            result.ai_insights.next_trip_suggestion.recommended_categories,
            ["restaurant", "shopping", "tourist_spot"],
        )

        openai_input = create.call_args.kwargs["input"]
        self.assertIn("First Place", openai_input)
        self.assertIn('"category": "restaurant"', openai_input)
        self.assertNotIn("distanceKm", openai_input)
        self.assertNotIn("tel", openai_input)
        self.assertNotIn("address", openai_input)

    def test_ai_retries_plain_json_when_json_schema_attempt_fails(self) -> None:
        create = Mock(
            side_effect=[
                RuntimeError("json schema not supported"),
                SimpleNamespace(output_text=ai_output()),
            ]
        )
        client = SimpleNamespace(responses=SimpleNamespace(create=create))

        with patch("app.services.report_service.settings.openai_api_key", "test-key"), patch(
            "app.services.report_service.OpenAI",
            return_value=client,
        ):
            result = self.service.generate_report(make_request())

        self.assertEqual(result.title, "AI title")
        self.assertIsNotNone(result.ai_insights)
        self.assertEqual(create.call_count, 2)
        self.assertEqual(create.call_args_list[0].kwargs["model"], "gpt-5-mini")
        self.assertEqual(create.call_args_list[1].kwargs["model"], "gpt-5-mini")
        self.assertIn("text", create.call_args_list[0].kwargs)
        self.assertNotIn("text", create.call_args_list[1].kwargs)

    def test_ai_invalid_json_wrong_description_count_missing_insights_and_exception_fallback(self) -> None:
        invalid_outputs = (
            "not json",
            '{"title":"T","summary":"S","timelineDescriptions":["one"],"overallReview":"O","aiInsights":{}}',
            '{"title":"T","summary":"S","timelineDescriptions":["one","two"],"overallReview":"O"}',
        )
        for output_text in invalid_outputs:
            create = Mock(return_value=SimpleNamespace(output_text=output_text))
            client = SimpleNamespace(responses=SimpleNamespace(create=create))
            with patch("app.services.report_service.settings.openai_api_key", "test-key"), patch(
                "app.services.report_service.OpenAI",
                return_value=client,
            ):
                result = self.service.generate_report(make_request())
            self.assertEqual(result.title, "AI가 정리해준 광주의 하루")
            self.assertIsNone(result.ai_insights)

        with patch("app.services.report_service.settings.openai_api_key", "test-key"), patch(
            "app.services.report_service.OpenAI",
            side_effect=RuntimeError("failure"),
        ):
            result = self.service.generate_report(make_request())
        self.assertEqual(result.title, "AI가 정리해준 광주의 하루")
        self.assertIsNone(result.ai_insights)


if __name__ == "__main__":
    unittest.main()
