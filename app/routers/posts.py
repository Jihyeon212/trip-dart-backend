import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.post import PostRecord
from app.schemas.post import PostCreate, PostResponse


router = APIRouter()

# FastAPI가 요청마다 get_db()를 실행해 Session을 넣어줍니다.
DbSession = Annotated[Session, Depends(get_db)]


def serialize_route_data(
    route_data: list[dict[str, Any]] | None,
) -> str | None:
    """여행 코스 배열을 SQLite에 저장할 JSON 문자열로 변환합니다."""
    if route_data is None:
        return None

    return json.dumps(
        route_data,
        ensure_ascii=False,
    )


def deserialize_route_data(
    route_data: str | None,
) -> list[dict[str, Any]] | None:
    """SQLite에 저장된 JSON 문자열을 응답용 배열로 변환합니다."""
    if not route_data:
        return None

    try:
        parsed_data = json.loads(route_data)

        if isinstance(parsed_data, list):
            return parsed_data

        return None
    except (json.JSONDecodeError, TypeError):
        return None


def to_post_response(post: PostRecord) -> PostResponse:
    """SQLAlchemy PostRecord 객체를 API 응답 스키마로 변환합니다."""
    return PostResponse(
        id=post.id,
        post_type=post.post_type,
        title=post.title,
        content=post.content,
        nickname=post.nickname,
        route_data=deserialize_route_data(post.route_data),
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.get(
    "",
    response_model=list[PostResponse],
)
def list_posts(
    db: DbSession,
) -> list[PostResponse]:
    """게시글을 최신순으로 조회합니다."""
    statement = select(PostRecord).order_by(PostRecord.id.desc())
    posts = db.scalars(statement).all()

    return [
        to_post_response(post)
        for post in posts
    ]


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    payload: PostCreate,
    db: DbSession,
) -> PostResponse:
    """새 게시글을 생성합니다."""
    db_post = PostRecord(
        post_type=payload.post_type,
        title=payload.title,
        content=payload.content,
        nickname=payload.nickname,
        password=payload.password,
        route_data=serialize_route_data(payload.route_data),
    )

    try:
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
    except SQLAlchemyError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 저장 중 오류가 발생했습니다.",
        ) from error

    return to_post_response(db_post)