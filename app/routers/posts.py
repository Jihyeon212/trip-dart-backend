import json
import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.post import PostRecord
from app.schemas.post import (
    PasswordRequest,
    PasswordVerificationResponse,
    PostCreate,
    PostListItem,
    PostListResponse,
    PostResponse,
    PostUpdate,
)


logger = logging.getLogger("uvicorn.error").getChild(__name__)

router = APIRouter(
    prefix="/api/posts",
    tags=["Posts"],
)

DbSession = Annotated[Session, Depends(get_db)]


def serialize_json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError(f"JSON으로 직렬화할 수 없는 값입니다: {type(value).__name__}")


def serialize_route_data(
    route_data: list[dict[str, Any]] | None,
) -> str | None:
    if route_data is None:
        return None
    return json.dumps(
        route_data,
        ensure_ascii=False,
        default=serialize_json_value,
    )


def deserialize_route_data(
    route_data: str | None,
) -> list[dict[str, Any]]:
    if not route_data:
        return []

    try:
        parsed_data = json.loads(route_data)
    except (json.JSONDecodeError, TypeError):
        logger.warning("게시글 route_data가 올바른 JSON 배열이 아닙니다.")
        return []

    if not isinstance(parsed_data, list):
        logger.warning("게시글 route_data JSON 값이 배열이 아닙니다.")
        return []
    return parsed_data


def to_post_response(post: PostRecord) -> PostResponse:
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


def get_post_or_404(post_id: int, db: Session) -> PostRecord:
    post = db.get(PostRecord, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다.",
        )
    return post


def verify_post_password(post: PostRecord, password: str) -> None:
    if post.password != password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비밀번호가 일치하지 않습니다.",
        )


@router.get("", response_model=PostListResponse)
def list_posts(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    keyword: str | None = None,
) -> PostListResponse:
    normalized_keyword = keyword.strip() if keyword else ""
    filters = []
    if normalized_keyword:
        filters.append(
            or_(
                PostRecord.title.contains(normalized_keyword),
                PostRecord.content.contains(normalized_keyword),
            )
        )

    total_statement = select(func.count(PostRecord.id)).where(*filters)
    total = db.scalar(total_statement) or 0

    statement = (
        select(PostRecord)
        .where(*filters)
        .order_by(PostRecord.created_at.desc(), PostRecord.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    posts = db.scalars(statement).all()

    return PostListResponse(
        items=[PostListItem.model_validate(post) for post in posts],
        page=page,
        size=size,
        total=total,
        total_pages=(total + size - 1) // size if total else 0,
    )


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(payload: PostCreate, db: DbSession) -> PostResponse:
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
        logger.exception("게시글 저장 중 DB 오류가 발생했습니다.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 저장 중 오류가 발생했습니다.",
        ) from error

    return to_post_response(db_post)


@router.post(
    "/{post_id}/verify-password",
    response_model=PasswordVerificationResponse,
)
def verify_password(
    post_id: Annotated[int, Path(ge=1)],
    payload: PasswordRequest,
    db: DbSession,
) -> PasswordVerificationResponse:
    post = get_post_or_404(post_id, db)
    verify_post_password(post, payload.password)
    return PasswordVerificationResponse(valid=True)


@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: Annotated[int, Path(ge=1)],
    db: DbSession,
) -> PostResponse:
    post = get_post_or_404(post_id, db)
    return to_post_response(post)


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: Annotated[int, Path(ge=1)],
    payload: PostUpdate,
    db: DbSession,
) -> PostResponse:
    try:
        post = get_post_or_404(post_id, db)
        verify_post_password(post, payload.password)

        post.post_type = payload.post_type
        post.title = payload.title
        post.content = payload.content
        post.nickname = payload.nickname
        post.route_data = serialize_route_data(payload.route_data)
        post.updated_at = datetime.now()

        db.commit()
        db.refresh(post)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 수정 중 오류가 발생했습니다.",
        ) from error

    return to_post_response(post)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post(
    post_id: Annotated[int, Path(ge=1)],
    payload: PasswordRequest,
    db: DbSession,
) -> Response:
    try:
        post = get_post_or_404(post_id, db)
        verify_post_password(post, payload.password)

        db.delete(post)
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 삭제 중 오류가 발생했습니다.",
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
