"""OpenAI 兼容的 /v1 接口，供外部调用"""
from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import get_db
from services.chat_service import chat

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "default"
    messages: List[ChatMessage]
    max_tokens: int = 2048
    stream: bool = False


@router.post("/chat/completions")
async def openai_chat_completions(req: ChatCompletionRequest, db=Depends(get_db)):
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    content = await chat(db, msgs)
    return {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@router.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [{"id": "default", "object": "model", "created": 0}],
    }
