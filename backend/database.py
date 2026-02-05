"""数据库连接和会话"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path

from config import settings


db_path = Path(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_rag_columns(conn)


async def _migrate_rag_columns(conn):
    """为已有表添加列（若不存在）"""
    from sqlalchemy import text
    def _run(sync_conn):
        try:
            sync_conn.execute(text("ALTER TABLE documents ADD COLUMN build_status VARCHAR(20) DEFAULT 'pending'"))
        except Exception:
            pass
        for col, spec in [
            ("embed_api_key", "VARCHAR(500)"),
            ("embed_api_base", "VARCHAR(500)"),
            ("use_ollama", "INTEGER DEFAULT 0"),
            ("ollama_base_url", "VARCHAR(255)"),
            ("use_siliconflow", "INTEGER DEFAULT 1"),
            ("siliconflow_api_key", "VARCHAR(500)"),
            ("siliconflow_base_url", "VARCHAR(500)"),
        ]:
            try:
                sync_conn.execute(text(f"ALTER TABLE rag_config ADD COLUMN {col} {spec}"))
            except Exception:
                pass
    await conn.run_sync(_run)
