"""初始化数据库：建表、默认管理员、默认 Prompt（可单独运行）"""
import asyncio
from sqlalchemy import select

from database import engine, AsyncSessionLocal, init_db
from models import User, UserRole, ModelConfig, PromptConfig
from auth import get_password_hash


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User))
        if r.scalar_one_or_none() is None:
            admin = User(
                username="admin",
                email="admin@local",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.teacher,
                is_active=1,
            )
            db.add(admin)
            print("已创建默认管理员: admin / admin123")

        r = await db.execute(select(PromptConfig))
        if r.scalar_one_or_none() is None:
            p = PromptConfig(
                name="默认",
                content="你是一个有帮助的AI助手。请基于提供的知识库内容回答用户问题。",
                is_default=True,
            )
            db.add(p)
            print("已创建默认 Prompt")

        r = await db.execute(select(ModelConfig))
        if r.scalar_one_or_none() is None:
            m = ModelConfig(
                name="Gemini",
                model_type="api",
                provider="gemini",
                model_name="gemini-2.0-flash",
                api_key=None,
                is_default=True,
            )
            db.add(m)
            print("已创建默认模型配置: Gemini（请在模型配置中填写 API Key，或在 .env 中设置 GEMINI_API_KEY）")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
