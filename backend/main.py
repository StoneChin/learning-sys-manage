"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # register all tables for create_all
from config import settings
from database import init_db
from api.auth import router as auth_router
from api.users import router as users_router
from api.models import router as models_router
from api.prompts import router as prompts_router
from api.chat import router as chat_router
from api.openai_compat import router as openai_router
from api.knowledge import router as knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    # shutdown if needed


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(openai_router, prefix="/v1")
