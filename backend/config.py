"""应用配置"""
from pydantic_settings import BaseSettings
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "RAG 学习管理系统"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_BASE / 'data' / 'learning_sys.db'}"

    # JWT 鉴权
    SECRET_KEY: str = "your-secret-key-change-in-production-learning-sys-manage-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # 模型路径
    LOCAL_MODELS_DIR: Path = _BASE / "models"
    RAG_DATA_DIR: Path = _BASE / "data" / "rag"
    UPLOAD_DIR: Path = _BASE / "data" / "uploads"

    # Neo4j（LightRAG 知识图谱存储）
    NEO4J_URI: str = "neo4j://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"

    # 硅基流动 API（默认）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    SILICONFLOW_LLM_MODEL: str = "Qwen/Qwen3-8B"
    SILICONFLOW_EMBED_MODEL: str = "Qwen/Qwen3-Embedding-4B"

    # 本地 Ollama
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_LLM_MODEL: str = "qwen3:8b"
    LOCAL_EMBED_MODEL: str = "Qwen/Qwen3-Embedding-4B"

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        # 优先从项目根目录加载 .env（与 .env.example 同目录）
        env_file = str(_BASE / ".env") if (_BASE / ".env").exists() else ".env"
        extra = "ignore"  # 允许 .env 中存在未在 Settings 中声明的变量（如 OPENAI_API_KEY）


settings = Settings()
