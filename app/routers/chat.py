from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    return ChatResponse(reply=f"Echo: {request.message}")
