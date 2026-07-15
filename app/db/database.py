from collections.abc import Generator
import logging
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "localhub.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

logger = logging.getLogger("uvicorn.error").getChild(__name__)

POST_COLUMN_MIGRATIONS = {
    "post_type": "VARCHAR(30) NOT NULL DEFAULT 'local_info'",
    "nickname": "VARCHAR(20) NOT NULL DEFAULT 'anonymous'",
    # 비밀번호가 없던 레거시 행에는 수정·삭제 가능한 기본 비밀번호를 부여하지 않습니다.
    "password": "VARCHAR(4) NOT NULL DEFAULT ''",
    "route_data": "TEXT",
    "updated_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00.000000'",
}

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
class Base(DeclarativeBase):
    pass


def migrate_posts_table() -> None:
    """이전 개발 DB의 posts 테이블에 누락된 컬럼을 데이터 보존 방식으로 추가합니다."""
    inspector = inspect(engine)
    if not inspector.has_table("posts"):
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("posts")
    }
    missing_columns = {
        name: definition
        for name, definition in POST_COLUMN_MIGRATIONS.items()
        if name not in existing_columns
    }
    if not missing_columns:
        return

    with engine.begin() as connection:
        for name, definition in missing_columns.items():
            connection.exec_driver_sql(
                f'ALTER TABLE posts ADD COLUMN "{name}" {definition}'
            )
            logger.info("posts 테이블에 누락 컬럼을 추가했습니다: %s", name)

        if "updated_at" in missing_columns:
            connection.exec_driver_sql(
                "UPDATE posts SET updated_at = "
                "COALESCE(created_at, CURRENT_TIMESTAMP)"
            )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    from app.models import post

    Base.metadata.create_all(bind=engine)
    migrate_posts_table()
