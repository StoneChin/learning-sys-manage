"""对话服务 - 支持 API/本地模型、RAG、自定义 Prompt、流式输出；支持 OpenAI、DeepSeek、Gemini"""
import os
from typing import List, Optional, AsyncGenerator
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import ModelConfig, PromptConfig
from services import lightrag_service

_MASKED = "***"


def _gemini_api_key(config: ModelConfig) -> str:
    raw = (config.api_key or "").strip()
    if raw == _MASKED or not raw:
        raw = ""
    return raw or os.getenv("GEMINI_API_KEY", "").strip()


def _get_client(config: ModelConfig) -> AsyncOpenAI:
    if config.provider == "gemini":
        raise ValueError("Gemini 使用专用路径，不应调用 _get_client")
    if config.model_type == "api":
        base_url = config.api_base or None
        if config.provider == "openai":
            base_url = config.api_base or "https://api.openai.com/v1"
        elif config.provider == "deepseek":
            base_url = config.api_base or "https://api.deepseek.com/v1"
        elif config.provider == "other":
            base_url = config.api_base
        return AsyncOpenAI(api_key=config.api_key or "", base_url=base_url)
    if config.model_type == "local":
        base_url = config.api_base or "http://127.0.0.1:8000/v1"
        return AsyncOpenAI(api_key="not-needed", base_url=base_url)
    raise ValueError(f"未知模型类型: {config.model_type}")


def _get_model_name(config: ModelConfig) -> str:
    if config.model_type == "api":
        return config.model_name or ("gemini-2.0-flash" if config.provider == "gemini" else "gpt-4")
    if config.model_type == "local":
        return config.model_name or config.local_path or "local"
    return config.model_name


async def get_default_model_config(db: AsyncSession) -> Optional[ModelConfig]:
    result = await db.execute(select(ModelConfig).where(ModelConfig.is_default == True))
    return result.scalar_one_or_none()


async def get_model_config_by_id(db: AsyncSession, config_id: int) -> Optional[ModelConfig]:
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == config_id))
    return result.scalar_one_or_none()


async def get_default_prompt(db: AsyncSession) -> str:
    result = await db.execute(select(PromptConfig).where(PromptConfig.is_default == True))
    p = result.scalar_one_or_none()
    return p.content if p else "你是一个有帮助的AI助手。"


async def get_prompt_by_id(db: AsyncSession, prompt_config_id: int) -> Optional[str]:
    result = await db.execute(select(PromptConfig).where(PromptConfig.id == prompt_config_id))
    p = result.scalar_one_or_none()
    return p.content if p else None


def _format_messages_for_gemini(full_messages: List[dict]) -> str:
    """将消息列表格式化为 Gemini 接受的单条文本（与 LightRAG 一致）。"""
    lines = []
    for m in full_messages:
        role = (m.get("role") or "user").lower()
        text = (m.get("content") or "").strip()
        if role == "system":
            lines.append(f"[system] {text}")
        elif role == "user":
            lines.append(f"[user] {text}")
        elif role == "assistant":
            lines.append(f"[model] {text}")
    return "\n".join(lines) if lines else ""


async def _chat_gemini(config: ModelConfig, full_messages: List[dict]) -> str:
    from google import genai
    key = _gemini_api_key(config)
    if not key:
        raise ValueError("请配置 Gemini API Key：在模型配置中填写或设置环境变量 GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    model_name = config.model_name or "gemini-2.0-flash"
    prompt = _format_messages_for_gemini(full_messages)
    if not prompt:
        return ""
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=[prompt],
        config=genai.types.GenerateContentConfig(max_output_tokens=2048),
    )
    if not response.candidates:
        return ""
    parts = response.candidates[0].content.parts if response.candidates[0].content else []
    if not parts:
        return ""
    return (parts[0].text or "").strip()


async def _chat_stream_gemini(config: ModelConfig, full_messages: List[dict]) -> AsyncGenerator[str, None]:
    from google import genai
    key = _gemini_api_key(config)
    if not key:
        raise ValueError("请配置 Gemini API Key：在模型配置中填写或设置环境变量 GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    model_name = config.model_name or "gemini-2.0-flash"
    prompt = _format_messages_for_gemini(full_messages)
    if not prompt:
        return
    stream = await client.aio.models.generate_content_stream(
        model=model_name,
        contents=[prompt],
        config=genai.types.GenerateContentConfig(max_output_tokens=2048),
    )
    async for chunk in stream:
        if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
            for p in chunk.candidates[0].content.parts:
                if p.text:
                    yield p.text


def _fallback_gemini_config():
    """无模型配置时，若 .env 有 GEMINI_API_KEY 则使用虚拟配置对象。"""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    from types import SimpleNamespace
    return SimpleNamespace(
        provider="gemini",
        model_name=os.getenv("LIGHTRAG_LLM_MODEL", "gemini-2.0-flash"),
        api_key=key,
    )


async def chat(
    db: AsyncSession,
    messages: List[dict],
    model_config_id: Optional[int] = None,
    kb_id: Optional[int] = None,
    system_prompt: Optional[str] = None,
    prompt_config_id: Optional[int] = None,
    use_rag: bool = True,
) -> str:
    config = None
    if model_config_id:
        config = await get_model_config_by_id(db, model_config_id)
    if not config:
        config = await get_default_model_config(db)
    if not config:
        config = _fallback_gemini_config()
    if not config:
        raise ValueError("请先在「模型配置」中添加并设置默认模型（支持 OpenAI、DeepSeek、Gemini），或在 .env 中配置 GEMINI_API_KEY")

    if system_prompt:
        system = system_prompt
    elif prompt_config_id:
        system = await get_prompt_by_id(db, prompt_config_id) or await get_default_prompt(db)
    else:
        system = await get_default_prompt(db)

    if kb_id and use_rag:
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            last_query = user_msgs[-1].get("content", "")
            if isinstance(last_query, str) and last_query.strip():
                try:
                    refs = await lightrag_service.search_rag(kb_id, last_query, top_k=3)
                    if refs:
                        context = "\n\n".join(refs)
                        system = f"{system}\n\n参考以下知识库内容回答用户问题：\n{context}"
                except Exception:
                    pass

    full_messages = [{"role": "system", "content": system}] + messages

    if getattr(config, "provider", "") == "gemini":
        return await _chat_gemini(config, full_messages)

    client = _get_client(config)
    model_name = _get_model_name(config)
    response = await client.chat.completions.create(
        model=model_name,
        messages=full_messages,
        max_tokens=2048,
    )
    choice = response.choices[0] if response.choices else None
    if not choice:
        return ""
    return choice.message.content or ""


async def chat_stream(
    db: AsyncSession,
    messages: List[dict],
    model_config_id: Optional[int] = None,
    kb_id: Optional[int] = None,
    system_prompt: Optional[str] = None,
    prompt_config_id: Optional[int] = None,
    use_rag: bool = True,
) -> AsyncGenerator[str, None]:
    config = None
    if model_config_id:
        config = await get_model_config_by_id(db, model_config_id)
    if not config:
        config = await get_default_model_config(db)
    if not config:
        config = _fallback_gemini_config()
    if not config:
        raise ValueError("请先在「模型配置」中添加并设置默认模型（支持 OpenAI、DeepSeek、Gemini），或在 .env 中配置 GEMINI_API_KEY")

    if system_prompt:
        system = system_prompt
    elif prompt_config_id:
        system = await get_prompt_by_id(db, prompt_config_id) or await get_default_prompt(db)
    else:
        system = await get_default_prompt(db)

    if kb_id and use_rag:
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if user_msgs:
            last_query = user_msgs[-1].get("content", "")
            if isinstance(last_query, str) and last_query.strip():
                try:
                    refs = await lightrag_service.search_rag(kb_id, last_query, top_k=3)
                    if refs:
                        context = "\n\n".join(refs)
                        system = f"{system}\n\n参考以下知识库内容回答用户问题：\n{context}"
                except Exception:
                    pass

    full_messages = [{"role": "system", "content": system}] + messages

    if getattr(config, "provider", None) == "gemini":
        async for chunk in _chat_stream_gemini(config, full_messages):
            yield chunk
        return

    client = _get_client(config)
    model_name = _get_model_name(config)
    stream = await client.chat.completions.create(
        model=model_name,
        messages=full_messages,
        max_tokens=2048,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
