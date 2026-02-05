"""模型和提示词配置"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime

from database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    # api / local
    model_type = Column(String(20), nullable=False, default="api")
    # openai / deepseek / local 等
    provider = Column(String(50), nullable=False)
    model_name = Column(String(200), nullable=False)  # API模型名或本地路径
    api_base = Column(String(500))  # API base URL
    api_key = Column(String(500))  # 加密存储
    local_path = Column(String(500))  # 本地模型路径
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptConfig(Base):
    __tablename__ = "prompt_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
