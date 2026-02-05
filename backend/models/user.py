"""用户和角色模型"""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from datetime import datetime
import enum

from database import Base


class UserRole(str, enum.Enum):
    teacher = "teacher"
    ta = "ta"
    student = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.student)
    full_name = Column(String(100))
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(100), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
