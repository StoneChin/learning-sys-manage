"""用户管理 API - 仅教师可管理助教"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from database import get_db
from models import User, UserRole
from auth import require_teacher, get_password_hash

router = APIRouter(prefix="/users", tags=["用户管理"])


class CreateTARequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None


class UpdateTARequest(BaseModel):
    full_name: str | None = None
    password: str | None = None
    is_active: int | None = None


@router.get("/ta")
async def list_ta(
    _user=Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.role == UserRole.ta))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/ta")
async def create_ta(
    req: CreateTARequest,
    _user=Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role=UserRole.ta,
        full_name=req.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return {"id": user.id, "username": user.username, "message": "助教已添加"}


@router.delete("/ta/{user_id}")
async def delete_ta(
    user_id: int,
    _user=Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id, User.role == UserRole.ta))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="助教不存在")
    await db.delete(user)
    return {"message": "已删除"}


@router.patch("/ta/{user_id}")
async def update_ta(
    user_id: int,
    req: UpdateTARequest,
    _user=Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id, User.role == UserRole.ta))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="助教不存在")
    if req.full_name is not None:
        user.full_name = req.full_name
    if req.password is not None:
        user.hashed_password = get_password_hash(req.password)
    if req.is_active is not None:
        user.is_active = req.is_active
    await db.flush()
    return {"message": "已更新"}
