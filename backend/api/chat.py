"""OpenAI 兼容的 Chat API"""
import json
from typing import Optional, List
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import get_db, AsyncSessionLocal
from auth import require_user
from services.chat_service import chat, chat_stream

router = APIRouter(prefix="/chat", tags=["对话"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    model_config_id: Optional[int] = None
    kb_id: Optional[int] = None
    system_prompt: Optional[str] = None
    prompt_config_id: Optional[int] = None
    stream: bool = False


async def _sse_generator(req):
    async with AsyncSessionLocal() as db:
        try:
            msgs = [{"role": m.role, "content": m.content} for m in req.messages]
            async for chunk in chat_stream(
                db,
                msgs,
                model_config_id=req.model_config_id,
                kb_id=req.kb_id,
                system_prompt=req.system_prompt,
                prompt_config_id=req.prompt_config_id,
            ):
                yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}, 'index': 0}]})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            await db.close()


@router.post("/completions")
async def chat_completions(
    req: ChatRequest,
    user=Depends(require_user),
    db=Depends(get_db),
):
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]

    if req.stream:
        return StreamingResponse(
            _sse_generator(req),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    content = await chat(
        db,
        msgs,
        model_config_id=req.model_config_id,
        kb_id=req.kb_id,
        system_prompt=req.system_prompt,
        prompt_config_id=req.prompt_config_id,
    )
    return {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@router.post("/search")
async def search_knowledge(
    kb_id: int,
    query: str,
    top_k: int = 5,
    user=Depends(require_user),
):
    from services import lightrag_service
    refs = await lightrag_service.search_rag(kb_id, query, top_k=top_k)
    return {"results": [{"content": r} for r in refs]}
