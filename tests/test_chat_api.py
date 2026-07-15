import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.models.post import PostRecord
from app.routers import chat
from app.schemas.location import Location


def location(contentid: str, title: str, category: str) -> Location:
    return Location(
        contentid=contentid,
        contenttypeid="14",
        category=category,
        category_name="문화시설" if category == "cultural_facility" else "음식점",
        title=title,
        addr1="광주광역시 동구",
        addr2="",
        tel="",
        longitude=126.9,
        latitude=35.1,
        image_url="",
        thumbnail_url="",
        sigungucode="3",
    )


class ChatApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, expire_on_commit=False)
        with cls.SessionLocal() as db:
            db.add(PostRecord(
                post_type="travel_review",
                title="문화전당 후기",
                content="문화전당이 좋았습니다.",
                nickname="작성자",
                password="0001",
            ))
            db.commit()

        app = FastAPI()
        app.include_router(chat.router)

        def override_get_db():
            with cls.SessionLocal() as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)
        cls.locations = [
            location("1", "국립아시아문화전당", "cultural_facility"),
            location("2", "광주시립미술관", "cultural_facility"),
            location("3", "문화예술회관", "cultural_facility"),
            location("4", "추가문화관", "cultural_facility"),
            location("5", "광주식당", "restaurant"),
        ]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def request(self, message: str, current_route=None):
        with patch(
            "app.services.chat_service.location_service.get_all_locations",
            return_value=self.locations,
        ), patch("app.services.chat_service.settings.openai_api_key", None):
            return self.client.post(
                "/api/chat",
                json={"message": message, "current_route": current_route or []},
            )

    def test_chat_category_place_and_post_queries(self) -> None:
        cultural = self.request("광주 문화시설 추천해줘")
        self.assertEqual(cultural.status_code, 200)
        self.assertLessEqual(len(cultural.json()["locations"]), 3)
        self.assertTrue(all(
            item["category"] == "cultural_facility"
            for item in cultural.json()["locations"]
        ))

        restaurant = self.request("광주 음식점 알려줘")
        self.assertTrue(all(
            item["category"] == "restaurant"
            for item in restaurant.json()["locations"]
        ))

        place_and_post = self.request("국립아시아문화전당 문화전당 후기 알려줘")
        self.assertEqual(place_and_post.json()["locations"][0]["contentid"], "1")
        self.assertGreaterEqual(len(place_and_post.json()["posts"]), 1)
        self.assertNotIn("password", place_and_post.text.lower())
        self.assertNotIn("0001", place_and_post.text)

    def test_route_no_results_empty_message_and_ai_failure(self) -> None:
        route = [
            {"contentid": "1", "title": "첫 번째", "category": "tourist_spot"},
            {"contentid": "2", "title": "두 번째", "category": "restaurant"},
        ]
        route_response = self.request("현재 코스 순서 설명해줘", route)
        answer = route_response.json()["answer"]
        self.assertLess(answer.index("첫 번째"), answer.index("두 번째"))

        with patch(
            "app.services.chat_service.location_service.get_all_locations",
            return_value=[],
        ), patch("app.services.chat_service.settings.openai_api_key", "test"), patch(
            "app.services.chat_service.OpenAI", side_effect=RuntimeError("failure")
        ):
            no_results = self.client.post(
                "/api/chat", json={"message": "우주선 탑승 위치", "current_route": []}
            )
        self.assertEqual(no_results.status_code, 200)
        self.assertEqual(
            no_results.json()["answer"],
            "현재 제공된 광주 지역 데이터에서는 해당 정보를 찾지 못했습니다.",
        )
        self.assertEqual(self.client.post("/api/chat", json={"message": "   "}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
