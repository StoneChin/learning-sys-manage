"""模型配置 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from models import ModelConfig
from auth import require_teacher_or_ta
from services.model_service import get_local_models, download_from_modelscope, get_modelscope_popular_models

router = APIRouter(prefix="/models", tags=["模型配置"])


class ModelConfigCreate(BaseModel):
    name: str
    model_type: str  # api / local
    provider: str  # openai / deepseek / local
    model_name: str
    api_base: str | None = None
    api_key: str | None = None
    local_path: str | None = None
    is_default: bool = False


class ModelConfigUpdate(BaseModel):
    name: str | None = None
    model_type: str | None = None
    provider: str | None = None
    model_name: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    local_path: str | None = None
    is_default: bool | None = None


@router.get("/local-list")
async def list_local_models(_=Depends(require_teacher_or_ta)):
    return {"models": get_local_models()}


@router.get("/modelscope-list")
async def list_modelscope_models(_=Depends(require_teacher_or_ta)):
    return {"models": get_modelscope_popular_models()}


@router.post("/modelscope-download")
async def modelscope_download(
    model_id: str,
    save_dir: str,
    _=Depends(require_teacher_or_ta),
):
    result = await download_from_modelscope(model_id, save_dir)
    return result


@router.get("")
async def list_configs(
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).order_by(ModelConfig.id))
    configs = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "model_type": c.model_type,
            "provider": c.provider,
            "model_name": c.model_name,
            "api_base": c.api_base,
            "api_key": "***" if c.api_key else None,
            "local_path": c.local_path,
            "is_default": c.is_default,
        }
        for c in configs
    ]


@router.post("")
async def create_config(
    req: ModelConfigCreate,
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    if req.is_default:
        await db.execute(ModelConfig.__table__.update().values(is_default=False))
    config = ModelConfig(
        name=req.name,
        model_type=req.model_type,
        provider=req.provider,
        model_name=req.model_name,
        api_base=req.api_base,
        api_key=req.api_key,
        local_path=req.local_path,
        is_default=req.is_default,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return {"id": config.id, "message": "已添加"}


@router.patch("/{config_id}")
async def update_config(
    config_id: int,
    req: ModelConfigUpdate,
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    if req.is_default:
        await db.execute(ModelConfig.__table__.update().values(is_default=False))
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(config, k, v)
    await db.flush()
    return {"message": "已更新"}


@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    _=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    await db.delete(config)
    return {"message": "已删除"}
