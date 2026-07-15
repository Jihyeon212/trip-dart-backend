import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.post import PostRecord
from app.schemas.chat import CurrentRouteLocation
from app.schemas.location import Location
from app.services.chat_service import ChatService, NO_RESULTS_ANSWER


def make_location(
    contentid: str,
    title: str,
    category: str,
    addr1: str = "광주광역시 동구",
) -> Location:
    return Location(
        contentid=contentid,
        contenttypeid="14",
        category=category,
        category_name="문화시설" if category == "cultural_facility" else "음식점",
        title=title,
        addr1=addr1,
        addr2="",
        tel="",
        longitude=126.9,
        latitude=35.1,
        image_url="",
        thumbnail_url="",
        sigungucode="3",
    )


class ChatServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ChatService()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.locations = [
            make_location("1", "국립아시아문화전당", "cultural_facility"),
            make_location("2", "광주시립미술관", "cultural_facility", "광주광역시 북구"),
            make_location("3", "빛고을문화관", "cultural_facility"),
            make_location("4", "네 번째 문화관", "cultural_facility"),
            make_location("5", "광주맛집", "restaurant"),
        ]

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_category_detection(self) -> None:
        self.assertEqual(self.service.detect_categories("문화시설 추천"), ["cultural_facility"])
        self.assertEqual(self.service.detect_categories("음식점 알려줘"), ["restaurant"])

    def test_category_title_address_search_and_limit(self) -> None:
        with patch(
            "app.services.chat_service.location_service.get_all_locations",
            return_value=self.locations,
        ):
            category = self.service.search_locations([], ["cultural_facility"])
            title = self.service.search_locations(["국립아시아문화전당"], [])
            address = self.service.search_locations(["북구"], [])

        self.assertEqual(len(category), 3)
        self.assertTrue(all(item.category == "cultural_facility" for item in category))
        self.assertEqual(title[0].contentid, "1")
        self.assertEqual(address[0].contentid, "2")
        self.assertEqual(
            self.service.extract_search_terms("동구에 있는 장소 알려줘", []),
            ["동구"],
        )

    def test_post_title_content_search_limit_and_no_password(self) -> None:
        for index in range(5):
            self.db.add(PostRecord(
                post_type="travel_review",
                title="문화전당 후기" if index == 0 else f"게시글 {index}",
                content="국립아시아문화전당 방문 내용",
                nickname="작성자",
                password="0001",
            ))
        self.db.commit()

        posts = self.service.search_posts(self.db, ["문화전당"])
        self.assertEqual(len(posts), 3)
        self.assertEqual(posts[0].title, "문화전당 후기")
        self.assertTrue(all("password" not in item.model_dump() for item in posts))

    def test_route_order_and_exact_no_results_answer(self) -> None:
        route = [
            CurrentRouteLocation(contentid="1", title="첫 번째", category="tourist_spot"),
            CurrentRouteLocation(contentid="2", title="두 번째", category="restaurant"),
        ]
        answer = self.service.build_route_answer(route)
        self.assertLess(answer.index("첫 번째"), answer.index("두 번째"))
        self.assertEqual(
            self.service.build_default_answer([], [], [], False, []),
            NO_RESULTS_ANSWER,
        )

    def test_general_location_and_post_intents_return_default_results(self) -> None:
        self.db.add(PostRecord(
            post_type="local_info",
            title="최신 지역 정보",
            content="내용",
            nickname="작성자",
            password="0001",
        ))
        self.db.commit()
        with patch(
            "app.services.chat_service.location_service.get_all_locations",
            return_value=self.locations,
        ), patch("app.services.chat_service.settings.openai_api_key", None):
            places = self.service.process_chat(self.db, "광주 장소 추천해줘", [])
            posts = self.service.process_chat(self.db, "게시글 보여줘", [])
        self.assertEqual(len(places.locations), 3)
        self.assertEqual(len(posts.posts), 1)

    def test_missing_key_and_openai_failure_use_fallback(self) -> None:
        location = self.locations[0]
        with patch(
            "app.services.chat_service.location_service.get_all_locations",
            return_value=[location],
        ), patch("app.services.chat_service.settings.openai_api_key", None):
            missing_key = self.service.process_chat(
                self.db, "문화시설 추천해줘", []
            )
        self.assertEqual(missing_key.answer, "광주에서 방문할 수 있는 문화시설입니다.")

        with patch(
            "app.services.chat_service.location_service.get_all_locations",
            return_value=[location],
        ), patch("app.services.chat_service.settings.openai_api_key", "test-key"), patch(
            "app.services.chat_service.OpenAI", side_effect=RuntimeError("failure")
        ):
            failure = self.service.process_chat(self.db, "문화시설 추천해줘", [])
        self.assertEqual(failure.answer, missing_key.answer)
        self.assertEqual(failure.locations, missing_key.locations)

    def test_openai_success_changes_only_answer_and_excludes_password(self) -> None:
        post = PostRecord(
            post_type="travel_review",
            title="문화전당 후기",
            content="문화전당 방문",
            nickname="작성자",
            password="0001",
        )
        self.db.add(post)
        self.db.commit()
        create = Mock(return_value=SimpleNamespace(output_text="AI 정리 답변"))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))

        with patch(
            "app.services.chat_service.location_service.get_all_locations",
            return_value=[self.locations[0]],
        ), patch("app.services.chat_service.settings.openai_api_key", "test-key"), patch(
            "app.services.chat_service.OpenAI", return_value=client
        ):
            result = self.service.process_chat(self.db, "문화전당 후기 알려줘", [])

        self.assertEqual(result.answer, "AI 정리 답변")
        self.assertEqual(len(result.locations), 1)
        self.assertEqual(len(result.posts), 1)
        openai_input = create.call_args.kwargs["input"]
        self.assertNotIn("password", openai_input.lower())
        self.assertNotIn("0001", openai_input)


if __name__ == "__main__":
    unittest.main()
