"""LightRAG 服务：仅三种 — 硅基流动（默认）、Gemini API、本地 Ollama。图存储 Neo4j。"""
import os
import asyncio
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any

import numpy as np
from openai import AsyncOpenAI

from config import settings

_rag_instances: dict[int, object] = {}
_local_embed_model = None

_MASKED_API_KEY = "***"


def _get_local_embed_model():
    global _local_embed_model
    if _local_embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError("请安装 sentence-transformers: pip install sentence-transformers") from e
        model_name = getattr(settings, "LOCAL_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B")
        _local_embed_model = SentenceTransformer(model_name)
    return _local_embed_model


def _local_embed_sync(texts: list) -> np.ndarray:
    model = _get_local_embed_model()
    arr = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr.astype(np.float64)


async def _local_embed(texts: list) -> np.ndarray:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _local_embed_sync, texts)


def _get_working_dir(kb_id: int) -> Path:
    path = settings.RAG_DATA_DIR / "lightrag" / str(kb_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _set_neo4j_env():
    os.environ["NEO4J_URI"] = settings.NEO4J_URI
    os.environ["NEO4J_USERNAME"] = settings.NEO4J_USERNAME
    os.environ["NEO4J_PASSWORD"] = settings.NEO4J_PASSWORD
    os.environ["NEO4J_DATABASE"] = settings.NEO4J_DATABASE


def _effective_api_key(config_val: Any, env_val: str) -> str:
    raw = (config_val or "").strip() if isinstance(config_val, str) else ""
    if raw == _MASKED_API_KEY or not raw:
        raw = ""
    return (env_val or "").strip() or raw


def _get_rag_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """从传入 config 解析；仅三种：硅基流动（默认）> Ollama > Gemini。"""
    c = config or {}
    if c.get("use_siliconflow") and (c.get("siliconflow_api_key") or "").strip() and (c.get("siliconflow_api_key") or "").strip() != _MASKED_API_KEY:
        base = (c.get("siliconflow_base_url") or "").strip() or getattr(settings, "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
        key = (c.get("siliconflow_api_key") or "").strip()
        return {
            "use_siliconflow": True,
            "siliconflow_base_url": base.rstrip("/"),
            "siliconflow_api_key": key,
            "llm_model": (c.get("llm_model") or "").strip() or getattr(settings, "SILICONFLOW_LLM_MODEL", "Qwen/Qwen3-8B"),
            "embed_model": (c.get("embed_model") or "").strip() or getattr(settings, "SILICONFLOW_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B"),
            "embedding_dim": 1024,
        }
    if c.get("use_ollama"):
        base = (c.get("ollama_base_url") or "").strip() or getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        return {
            "use_ollama": True,
            "ollama_base_url": base.rstrip("/"),
            "llm_model": (c.get("llm_model") or "").strip() or getattr(settings, "OLLAMA_LLM_MODEL", "qwen3:8b"),
            "embed_model": (c.get("embed_model") or "").strip() or getattr(settings, "LOCAL_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B"),
            "embedding_dim": 1024,
        }
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    api_key = _effective_api_key(c.get("api_key"), env_key)
    return {
        "use_ollama": False,
        "use_siliconflow": False,
        "api_key": api_key,
        "llm_model": (c.get("llm_model") or "gemini-2.0-flash").strip(),
        "embed_model": (c.get("embed_model") or "gemini-embedding-001").strip(),
        "embedding_dim": 1536,
    }


async def _get_rag(kb_id: int, config: Optional[Dict[str, Any]] = None):
    if kb_id in _rag_instances:
        return _rag_instances[kb_id]
    _set_neo4j_env()
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.utils import EmbeddingFunc, wrap_embedding_func_with_attrs
    except ImportError as e:
        raise RuntimeError("请安装 lightrag-hku: pip install lightrag-hku") from e

    cfg = _get_rag_config(config)
    use_sf = cfg.get("use_siliconflow", False)
    use_ollama = cfg.get("use_ollama", False)
    llm_model = cfg["llm_model"]
    embed_model = cfg["embed_model"]
    embedding_dim = cfg["embedding_dim"]
    working_dir = str(_get_working_dir(kb_id))
    workspace = str(kb_id)

    if use_sf:
        from openai import AsyncOpenAI
        base_url = cfg.get("siliconflow_base_url", "https://api.siliconflow.cn/v1").rstrip("/")
        api_key = (cfg.get("siliconflow_api_key") or "").strip()
        if not api_key or api_key == _MASKED_API_KEY:
            raise ValueError("请配置硅基流动 API Key：.env 中设置 SILICONFLOW_API_KEY 或在知识库「LightRAG 配置」中填写")
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)

        async def llm_func(prompt, system_prompt=None, history_messages=None, **kwargs):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.extend((history_messages or []))
            messages.append({"role": "user", "content": prompt})
            r = await client.chat.completions.create(model=llm_model, messages=messages, max_tokens=2048)
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content
            return ""

        async def async_embed(texts: list) -> np.ndarray:
            r = await client.embeddings.create(model=embed_model, input=texts)
            vecs = [d.embedding for d in (r.data or [])]
            if not vecs:
                return np.zeros((len(texts), embedding_dim), dtype=np.float64)
            arr = np.array(vecs, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return arr

        try:
            probe = await async_embed(["probe"])
            if probe.size > 0 and probe.ndim >= 2:
                embedding_dim = int(probe.shape[1])
        except Exception:
            pass

    elif use_ollama:
        from openai import AsyncOpenAI
        base_url = cfg["ollama_base_url"]
        openai_base = f"{base_url.rstrip('/')}/v1" if not base_url.endswith("/v1") else base_url

        async def llm_func(prompt, system_prompt=None, history_messages=None, **kwargs):
            client_ollama = AsyncOpenAI(base_url=openai_base, api_key="ollama")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.extend((history_messages or []))
            messages.append({"role": "user", "content": prompt})
            r = await client_ollama.chat.completions.create(model=llm_model, messages=messages, max_tokens=2048)
            if r.choices and r.choices[0].message.content:
                return r.choices[0].message.content
            return ""

        async def async_embed(texts: list) -> np.ndarray:
            return await _local_embed(texts)

        try:
            probe = await _local_embed(["probe"])
            if probe.size > 0 and probe.ndim >= 2:
                embedding_dim = int(probe.shape[1])
            else:
                embedding_dim = getattr(_get_local_embed_model(), "get_sentence_embedding_dimension", lambda: 1024)()
        except Exception:
            try:
                embedding_dim = _get_local_embed_model().get_sentence_embedding_dimension()
            except Exception:
                embedding_dim = 1024

    else:
        api_key = cfg["api_key"]
        if not api_key or api_key == _MASKED_API_KEY:
            raise ValueError("请配置 Gemini API Key：在知识库「LightRAG 配置」中填写或 .env 中设置 GEMINI_API_KEY")
        try:
            from lightrag.llm.gemini import gemini_complete_if_cache, gemini_embed
        except ImportError as e:
            raise RuntimeError("使用 Gemini 请安装: pip install google-genai") from e

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
                embedding_dim = int(probe.shape[1])
        except Exception:
            pass

        async def async_embed(texts: list) -> np.ndarray:
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
        def sync_embed_wrapper(texts: list) -> np.ndarray:
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
    global _rag_instances
    _rag_instances.pop(kb_id, None)
    path = _get_working_dir(kb_id)
    import shutil
    if path.exists():
        try:
            shutil.rmtree(path)
        except Exception:
            pass
