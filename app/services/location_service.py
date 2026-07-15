import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.location import Location


logger = logging.getLogger("uvicorn.error").getChild(__name__)

CATEGORY_CONFIG = {
    "tourist_spot": {
        "file": "광주_전라권_관광지.json",
        "content_type_id": "12",
        "name": "관광지",
    },
    "cultural_facility": {
        "file": "광주_전라권_문화시설.json",
        "content_type_id": "14",
        "name": "문화시설",
    },
    "leisure_sports": {
        "file": "광주_전라권_레포츠.json",
        "content_type_id": "28",
        "name": "레포츠",
    },
    "shopping": {
        "file": "광주_전라권_쇼핑.json",
        "content_type_id": "38",
        "name": "쇼핑",
    },
    "restaurant": {
        "file": "광주_전라권_음식점.json",
        "content_type_id": "39",
        "name": "음식점",
    },
}


class LocationService:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path(__file__).resolve().parent.parent / "data"
        self._locations: list[Location] = []
        self._loaded = False
        self.excluded_count = 0
        self.duplicate_count = 0
        self.category_counts: dict[str, int] = {}

    @staticmethod
    def _as_string(value: Any) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _extract_items(data: Any) -> list[Any]:
        if not isinstance(data, dict):
            raise ValueError("JSON 최상위 값이 객체가 아닙니다.")

        node: Any = data
        if "response" in node:
            node = node["response"]
        if isinstance(node, dict) and "body" in node:
            node = node["body"]
        if isinstance(node, dict) and "items" in node:
            node = node["items"]
        else:
            raise ValueError("JSON에서 items를 찾을 수 없습니다.")
        if isinstance(node, dict) and "item" in node:
            node = node["item"]

        if isinstance(node, list):
            return node
        if isinstance(node, dict):
            return [node]
        raise ValueError("JSON의 장소 데이터가 배열 또는 객체가 아닙니다.")

    def _to_location(
        self,
        item: Any,
        category: str,
        config: dict[str, str],
    ) -> Location | None:
        if not isinstance(item, dict):
            return None

        contentid = self._as_string(item.get("contentid"))
        title = self._as_string(item.get("title"))
        mapx = self._as_string(item.get("mapx"))
        mapy = self._as_string(item.get("mapy"))
        if not contentid or not title or not mapx or not mapy:
            return None

        try:
            longitude = float(mapx)
            latitude = float(mapy)
        except (TypeError, ValueError):
            return None

        contenttypeid = self._as_string(item.get("contenttypeid"))
        return Location(
            contentid=contentid,
            contenttypeid=contenttypeid or config["content_type_id"],
            category=category,
            category_name=config["name"],
            title=title,
            addr1=self._as_string(item.get("addr1")),
            addr2=self._as_string(item.get("addr2")),
            tel=self._as_string(item.get("tel")),
            longitude=longitude,
            latitude=latitude,
            image_url=self._as_string(item.get("firstimage")),
            thumbnail_url=self._as_string(item.get("firstimage2")),
            sigungucode=self._as_string(item.get("sigungucode")),
            distance_km=None,
        )

    def load_locations(self) -> list[Location]:
        if self._loaded:
            return self._locations

        locations: list[Location] = []
        seen_content_ids: set[str] = set()
        excluded_count = 0
        duplicate_count = 0
        category_counts = {category: 0 for category in CATEGORY_CONFIG}

        for category, config in CATEGORY_CONFIG.items():
            file_path = self.data_dir / config["file"]
            try:
                with file_path.open(encoding="utf-8-sig") as file:
                    items = self._extract_items(json.load(file))
            except (OSError, json.JSONDecodeError, ValueError):
                logger.exception("장소 데이터 파일을 불러오지 못했습니다: %s", file_path)
                raise

            for item in items:
                location = self._to_location(item, category, config)
                if location is None:
                    excluded_count += 1
                    continue
                if location.contentid in seen_content_ids:
                    duplicate_count += 1
                    continue

                seen_content_ids.add(location.contentid)
                locations.append(location)
                category_counts[category] += 1

        self._locations = locations
        self._loaded = True
        self.excluded_count = excluded_count
        self.duplicate_count = duplicate_count
        self.category_counts = category_counts

        logger.info("전체 장소 %d건을 메모리에 로드했습니다.", len(locations))
        for category, count in category_counts.items():
            logger.info("카테고리 %s: %d건", category, count)
        logger.info("유효하지 않아 제외된 장소: %d건", excluded_count)
        logger.info("중복으로 제거된 장소: %d건", duplicate_count)

        return self._locations

    def get_all_locations(self) -> list[Location]:
        return self.load_locations()

    def get_locations_by_category(self, category: str) -> list[Location]:
        return [
            location
            for location in self.get_all_locations()
            if location.category == category
        ]

    def get_location_by_content_id(self, content_id: str) -> Location | None:
        normalized_content_id = content_id.strip()
        return next(
            (
                location
                for location in self.get_all_locations()
                if location.contentid == normalized_content_id
            ),
            None,
        )

    def reload_locations(self) -> list[Location]:
        self._locations = []
        self._loaded = False
        self.excluded_count = 0
        self.duplicate_count = 0
        self.category_counts = {}
        return self.load_locations()


location_service = LocationService()
