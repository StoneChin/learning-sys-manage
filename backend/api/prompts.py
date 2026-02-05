"""自定义 Prompt 配置 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from models import PromptConfig
from auth import require_teacher_or_ta

router = APIRouter(prefix="/prompts", tags=["Prompt 配置"])


class PromptCreate(BaseModel):
    name: str
    content: str
    is_default: bool = False


class PromptUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    is_default: bool | None = None


@router.get("")
async def list_prompts(
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptConfig).order_by(PromptConfig.id))
    prompts = result.scalars().all()
    return [{"id": p.id, "name": p.name, "content": p.content, "is_default": p.is_default} for p in prompts]


@router.post("")
async def create_prompt(
    req: PromptCreate,
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    if req.is_default:
        await db.execute(PromptConfig.__table__.update().values(is_default=False))
    p = PromptConfig(name=req.name, content=req.content, is_default=req.is_default)
    db.add(p)
    await db.flush()
    await db.refresh(p)
    return {"id": p.id}


@router.patch("/{prompt_id}")
async def update_prompt(
    prompt_id: int,
    req: PromptUpdate,
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptConfig).where(PromptConfig.id == prompt_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="不存在")
    if req.is_default:
        await db.execute(PromptConfig.__table__.update().values(is_default=False))
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.flush()
    return {"message": "已更新"}


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: int,
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptConfig).where(PromptConfig.id == prompt_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="不存在")
    await db.delete(p)
    return {"message": "已删除"}
