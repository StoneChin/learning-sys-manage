"""知识库和文档模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime

from database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    kg_status = Column(String(20), default="pending")  # pending / building / success / failed
    kg_progress = Column(Integer, default=0)
    kg_error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, default=0)
    status = Column(String(20), default="uploaded")  # uploaded / failed
    build_status = Column(String(20), default="pending")  # pending / building / built / failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RAGConfig(Base):
    """LightRAG 仅使用 Gemini API（单行）。"""
    __tablename__ = "rag_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key = Column(String(500))  # Gemini API Key
    api_base = Column(String(500))  # 保留列兼容，未使用
    llm_model = Column(String(100), default="gemini-2.0-flash")
    embed_model = Column(String(100), default="gemini-embedding-001")
    embed_api_key = Column(String(500))  # 保留列兼容，未使用
    embed_api_base = Column(String(500))  # 保留列兼容，未使用
