"""LightRAG 服务：仅使用 Gemini API（LLM + Embedding），参考官方用例；图存储使用 Neo4j。"""
import os
import asyncio
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any

from config import settings

_rag_instances: dict[int, object] = {}


def _get_working_dir(kb_id: int) -> Path:
    path = settings.RAG_DATA_DIR / "lightrag" / str(kb_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _set_neo4j_env():
    os.environ["NEO4J_URI"] = settings.NEO4J_URI
    os.environ["NEO4J_USERNAME"] = settings.NEO4J_USERNAME
    os.environ["NEO4J_PASSWORD"] = settings.NEO4J_PASSWORD
    os.environ["NEO4J_DATABASE"] = settings.NEO4J_DATABASE


_MASKED_API_KEY = "***"  # 与 api/knowledge 一致：占位符绝不传给 Gemini，优先用 .env


def _effective_api_key(config_val: Any, env_val: str) -> str:
    """解析有效 api_key：config 中的占位符或空视为未配置，优先用 .env。"""
    raw = (config_val or "").strip() if isinstance(config_val, str) else ""
    if raw == _MASKED_API_KEY or not raw:
        raw = ""
    return (env_val or "").strip() or raw


def _get_rag_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """从 config 或环境变量读取 Gemini 配置；.env 优先，占位符 *** 绝不使用。"""
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    api_key = _effective_api_key((config or {}).get("api_key"), env_key)
    llm_model = (config or {}).get("llm_model") or os.getenv("LIGHTRAG_LLM_MODEL", "gemini-2.0-flash")
    embed_model = (config or {}).get("embed_model") or os.getenv("LIGHTRAG_EMBED_MODEL", "gemini-embedding-001")
    return {
        "api_key": api_key,
        "llm_model": (llm_model or "gemini-2.0-flash").strip(),
        "embed_model": (embed_model or "gemini-embedding-001").strip(),
        "embedding_dim": 1536,
    }


async def _get_rag(kb_id: int, config: Optional[Dict[str, Any]] = None):
    """创建或返回该知识库的 LightRAG 实例，LLM 与 Embedding 均使用 Gemini（官方用法）。"""
    if kb_id in _rag_instances:
        return _rag_instances[kb_id]
    _set_neo4j_env()
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.llm.gemini import gemini_complete_if_cache, gemini_embed
        from lightrag.utils import EmbeddingFunc, wrap_embedding_func_with_attrs
        import numpy as np
    except ImportError as e:
        raise RuntimeError("请安装 lightrag-hku 与 google-genai: pip install lightrag-hku google-genai") from e

    cfg = _get_rag_config(config)
    api_key = cfg["api_key"]
    llm_model = cfg["llm_model"]
    embed_model = cfg["embed_model"]
    embedding_dim = cfg["embedding_dim"]

    if not api_key or api_key == _MASKED_API_KEY:
        raise ValueError(
            "请配置有效的 Gemini API Key：在知识库页「LightRAG 配置」中填写并保存，或在项目根目录 .env 中设置 GEMINI_API_KEY。"
        )

    working_dir = str(_get_working_dir(kb_id))
    workspace = str(kb_id)

    async def llm_func(prompt, system_prompt=None, history_messages=None, **kwargs):
        return await gemini_complete_if_cache(
            llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            api_key=api_key,
            keyword_extraction=kwargs.get("keyword_extraction", False),
            **{k: v for k, v in kwargs.items() if k not in ("response_format",)},
        )

    # 探测 API 实际返回的嵌入维度，避免与 LightRAG 期望的 embedding_dim 不一致导致报错
    try:
        probe = await gemini_embed.func(
            ["dimension probe"],
            model=embed_model,
            api_key=api_key,
            base_url=None,
            embedding_dim=embedding_dim,
            task_type="RETRIEVAL_DOCUMENT",
        )
        if probe.size > 0 and hasattr(probe, "shape") and len(probe.shape) >= 2:
            actual_dim = int(probe.shape[1])
            if actual_dim != embedding_dim:
                embedding_dim = actual_dim
    except Exception as e:
        # 探测失败时仍使用配置的 embedding_dim
        pass

    async def async_embed(texts: list) -> "np.ndarray":
        return await gemini_embed.func(
            texts,
            model=embed_model,
            api_key=api_key,
            base_url=None,
            embedding_dim=embedding_dim,
            task_type="RETRIEVAL_DOCUMENT",
        )

    main_loop = asyncio.get_running_loop()
    try:
        embedding_func = wrap_embedding_func_with_attrs(
            embedding_dim=embedding_dim,
            max_token_size=2048,
            model_name=embed_model,
        )(async_embed)
    except Exception:
        def sync_embed_wrapper(texts: list) -> "np.ndarray":
            future = asyncio.run_coroutine_threadsafe(async_embed(texts), main_loop)
            return future.result()

        try:
            embedding_func = wrap_embedding_func_with_attrs(
                embedding_dim=embedding_dim,
                max_token_size=2048,
                model_name=embed_model,
            )(sync_embed_wrapper)
        except Exception:
            embedding_func = EmbeddingFunc(
                embedding_dim=embedding_dim,
                max_token_size=2048,
                model_name=embed_model,
                func=sync_embed_wrapper,
            )

    rag = LightRAG(
        working_dir=working_dir,
        workspace=workspace,
        graph_storage="Neo4JStorage",
        llm_model_func=llm_func,
        embedding_func=embedding_func,
        addon_params={"language": "Chinese"},
    )
    await rag.initialize_storages()
    _rag_instances[kb_id] = rag
    return rag


async def insert_text(
    kb_id: int,
    text: str,
    config: Optional[Dict[str, Any]] = None,
    on_progress: Optional[Callable[..., None]] = None,
) -> None:
    """插入文本并构建 RAG 与知识图谱。"""
    if on_progress:
        on_progress(0, "building")
    try:
        rag = await _get_rag(kb_id, config=config)
        await rag.ainsert(text)
        if on_progress:
            on_progress(100, "success")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        if on_progress:
            try:
                on_progress(0, "failed", err_msg)
            except Exception:
                on_progress(0, "failed")
        raise e


async def search_rag(kb_id: int, query: str, top_k: int = 5, config: Optional[Dict[str, Any]] = None) -> List[str]:
    """检索知识库，返回上下文列表。"""
    from lightrag import QueryParam
    rag = await _get_rag(kb_id, config=config)
    result = await rag.aquery(
        query,
        param=QueryParam(mode="hybrid", only_need_context=True, top_k=top_k),
    )
    if isinstance(result, str):
        return [result] if result.strip() else []
    if isinstance(result, list):
        return result
    return []


def delete_kb_rag(kb_id: int) -> None:
    """删除该知识库的 RAG 缓存；Neo4j 图数据需另调 neo4j_kg_service.delete_workspace。"""
    global _rag_instances
    _rag_instances.pop(kb_id, None)
    path = _get_working_dir(kb_id)
    import shutil
    if path.exists():
        try:
            shutil.rmtree(path)
        except Exception:
            pass
