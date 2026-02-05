"""认证 API"""
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, UserRole, PasswordReset
from auth import get_password_hash, verify_password, create_access_token, require_user
from schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["认证"])


def _user_to_response(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
    }


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == req.username, User.is_active == 1)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token, user=_user_to_response(user))


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    role = UserRole.student
    if req.role in ("teacher", "ta"):
        role = UserRole(req.role)

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role=role,
        full_name=req.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token, user=_user_to_response(user))


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "如果该邮箱已注册，您将收到重置链接"}
    token = secrets.token_urlsafe(32)
    reset = PasswordReset(
        email=req.email,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(reset)
    await db.flush()
    return {"message": "如果该邮箱已注册，您将收到重置链接", "reset_token": token}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token == req.token,
            PasswordReset.used == 0,
            PasswordReset.expires_at > datetime.utcnow(),
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise HTTPException(status_code=400, detail="链接无效或已过期")
    result = await db.execute(select(User).where(User.email == reset.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")
    user.hashed_password = get_password_hash(req.new_password)
    reset.used = 1
    return {"message": "密码已重置"}


@router.get("/me", response_model=UserResponse)
async def get_me(user=Depends(require_user)):
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        full_name=user.full_name,
        is_active=user.is_active,
    )
