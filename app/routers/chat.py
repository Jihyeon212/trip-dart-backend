from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: DbSession) -> ChatResponse:
    return chat_service.process_chat(
        db=db,
        message=request.message,
        current_route=request.current_route,
    )
