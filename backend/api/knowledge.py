"""知识库与文档 API：CRUD、上传（仅保存）、构建按钮、状态轮询、RAG 配置、知识图谱查询"""
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, AsyncSessionLocal
from auth import require_teacher_or_ta
from models import KnowledgeBase, Document, RAGConfig
from config import settings
from services import lightrag_service
from services import neo4j_kg_service
from services.rag_service import _extract_text

router = APIRouter(prefix="/knowledge", tags=["知识库"])

# 前端显示占位符，表示「已有 Key 但不可见」；调用 API 时绝不使用，一律视为未配置
_MASKED_API_KEY = "***"


def _is_masked_or_empty(val: Optional[str]) -> bool:
    """判断是否为占位符或空，此类值绝不能传给 Gemini API。"""
    v = (val or "").strip()
    return v == _MASKED_API_KEY or v == ""


def _effective_api_key(db_val: Optional[str], env_val: str) -> str:
    """解析出有效的 api_key：db 中的占位符或空视为未配置，优先用 .env。"""
    raw = (db_val or "").strip()
    if _is_masked_or_empty(raw if raw else None):
        raw = ""
    return (env_val or "").strip() or raw


# 构建进度内存缓存：kb_id -> { "progress", "status", "error" }
_build_status: dict[int, dict] = {}


def _update_build_status(kb_id: int, progress: int, status: str, error: Optional[str] = None):
    _build_status[kb_id] = {"progress": progress, "status": status, "error": error}


async def _persist_kg_status(kb_id: int, progress: int, status: str, error: Optional[str] = None):
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        kb = r.scalar_one_or_none()
        if kb:
            kb.kg_progress = progress
            kb.kg_status = status
            kb.kg_error = error
            await db.commit()


async def _persist_docs_build_status(kb_id: int, status: str):
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(Document).where(Document.kb_id == kb_id, Document.build_status == "building"))
        for doc in r.scalars().all():
            doc.build_status = status
        await db.commit()


def _user_facing_error(e: Exception) -> str:
    """将异常转为用户可读的构建失败信息。"""
    import traceback
    err_str = str(e).lower()
    if "api key not valid" in err_str or "api_key_invalid" in err_str or ("invalid_argument" in err_str and "key" in err_str):
        return "Gemini API Key 无效或已过期。请在「LightRAG 配置」中重新填写有效的 API Key，或在项目根目录 .env 中设置 GEMINI_API_KEY。"
    if "please pass a valid api key" in err_str:
        return "未提供有效的 Gemini API Key。请在「LightRAG 配置」中保存 API Key，或在 .env 中配置 GEMINI_API_KEY。"
    if "bound to a different event loop" in err_str or "different event loop" in err_str:
        return "构建调度异常，请刷新页面后重试。"
    return f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}"


async def _run_build_async(kb_id: int, text: str, config: Optional[Dict[str, Any]] = None):
    """在主事件循环中执行构建，避免 LightRAG 内部 asyncio 锁跨事件循环报错。"""
    def on_progress(progress: int, status: str, error_detail: Optional[str] = None):
        err = error_detail if status == "failed" and error_detail else (None if status != "failed" else "构建失败")
        _update_build_status(kb_id, progress, status, err)
        if status in ("success", "failed"):
            asyncio.create_task(_persist_kg_status(kb_id, progress, status, err))

    try:
        await lightrag_service.insert_text(kb_id, text, config=config, on_progress=on_progress)
        await _persist_docs_build_status(kb_id, "built")
        _update_build_status(kb_id, 100, "success", None)
        await _persist_kg_status(kb_id, 100, "success", None)
    except Exception as e:
        err_msg = _user_facing_error(e)
        _update_build_status(kb_id, 0, "failed", err_msg)
        await _persist_kg_status(kb_id, 0, "failed", err_msg)
        await _persist_docs_build_status(kb_id, "failed")
    finally:
        # 构建完成后可保留 RAG 实例供后续查询；若需每次从磁盘加载可在此 pop
        pass


# --- Schemas ---
class KBCreate(BaseModel):
    name: str
    description: Optional[str] = None


class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class KBOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    kg_status: str
    kg_progress: int
    kg_error: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class DocOut(BaseModel):
    id: int
    kb_id: int
    filename: str
    file_type: str
    status: str
    build_status: str  # pending / building / built / failed
    created_at: Optional[str]

    class Config:
        from_attributes = True


def _is_masked_or_empty_sf(val: Optional[str]) -> bool:
    v = (val or "").strip()
    return v == _MASKED_API_KEY or v == ""


class RAGConfigOut(BaseModel):
    """LightRAG：硅基流动（默认）/ Gemini / 本地 Ollama。"""
    api_key: Optional[str] = None
    llm_model: Optional[str] = None
    embed_model: Optional[str] = None
    use_ollama: bool = False
    ollama_base_url: Optional[str] = None
    use_siliconflow: bool = True
    siliconflow_api_key: Optional[str] = None
    siliconflow_base_url: Optional[str] = None


class RAGConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    llm_model: Optional[str] = None
    embed_model: Optional[str] = None
    use_ollama: Optional[bool] = None
    ollama_base_url: Optional[str] = None
    use_siliconflow: Optional[bool] = None
    siliconflow_api_key: Optional[str] = None
    siliconflow_base_url: Optional[str] = None


# --- RAG 配置（硅基流动 默认 / Gemini / 本地 Ollama）---
@router.get("/rag-config", response_model=RAGConfigOut)
async def get_rag_config(
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    import os
    r = await db.execute(select(RAGConfig).limit(1))
    row = r.scalar_one_or_none()
    if not row:
        row = RAGConfig(
            llm_model=getattr(settings, "SILICONFLOW_LLM_MODEL", "Qwen/Qwen3-8B"),
            embed_model=getattr(settings, "SILICONFLOW_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B"),
        )
        db.add(row)
        await db.flush()
    use_ollama = bool(getattr(row, "use_ollama", 0))
    use_sf = bool(getattr(row, "use_siliconflow", 1))
    ollama_base = getattr(row, "ollama_base_url", None) or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    sf_base = (getattr(row, "siliconflow_base_url", None) or "").strip() or getattr(settings, "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    return RAGConfigOut(
        api_key=_MASKED_API_KEY if not _is_masked_or_empty(row.api_key) else "",
        llm_model=row.llm_model or ("qwen3:8b" if use_ollama else (getattr(settings, "SILICONFLOW_LLM_MODEL", "Qwen/Qwen3-8B") if use_sf else "gemini-2.0-flash")),
        embed_model=row.embed_model or ("Qwen/Qwen3-Embedding-4B" if use_ollama else (getattr(settings, "SILICONFLOW_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B") if use_sf else "gemini-embedding-001")),
        use_ollama=use_ollama,
        ollama_base_url=ollama_base,
        use_siliconflow=use_sf,
        siliconflow_api_key=_MASKED_API_KEY if not _is_masked_or_empty_sf(getattr(row, "siliconflow_api_key", None) or "") else "",
        siliconflow_base_url=sf_base,
    )


@router.patch("/rag-config", response_model=RAGConfigOut)
async def update_rag_config(
    body: RAGConfigUpdate,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    import os
    r = await db.execute(select(RAGConfig).limit(1))
    row = r.scalar_one_or_none()
    if not row:
        row = RAGConfig()
        db.add(row)
        await db.flush()
    if body.api_key is not None and not _is_masked_or_empty(body.api_key):
        row.api_key = body.api_key
    if body.llm_model is not None:
        row.llm_model = body.llm_model
    if body.embed_model is not None:
        row.embed_model = body.embed_model
    if body.use_ollama is not None:
        row.use_ollama = 1 if body.use_ollama else 0
    if body.ollama_base_url is not None:
        row.ollama_base_url = body.ollama_base_url.strip() or None
    if body.use_siliconflow is not None:
        row.use_siliconflow = 1 if body.use_siliconflow else 0
    if body.siliconflow_api_key is not None and not _is_masked_or_empty_sf(body.siliconflow_api_key):
        row.siliconflow_api_key = body.siliconflow_api_key.strip() or None
    if body.siliconflow_base_url is not None:
        row.siliconflow_base_url = body.siliconflow_base_url.strip() or None
    await db.flush()
    await db.refresh(row)
    use_ollama = bool(getattr(row, "use_ollama", 0))
    use_sf = bool(getattr(row, "use_siliconflow", 1))
    ollama_base = getattr(row, "ollama_base_url", None) or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    sf_base = (getattr(row, "siliconflow_base_url", None) or "").strip() or getattr(settings, "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    return RAGConfigOut(
        api_key=_MASKED_API_KEY if not _is_masked_or_empty(row.api_key) else "",
        llm_model=row.llm_model or ("qwen3:8b" if use_ollama else (getattr(settings, "SILICONFLOW_LLM_MODEL", "Qwen/Qwen3-8B") if use_sf else "gemini-2.0-flash")),
        embed_model=row.embed_model or ("Qwen/Qwen3-Embedding-4B" if use_ollama else (getattr(settings, "SILICONFLOW_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B") if use_sf else "gemini-embedding-001")),
        use_ollama=use_ollama,
        ollama_base_url=ollama_base,
        use_siliconflow=use_sf,
        siliconflow_api_key=_MASKED_API_KEY if not _is_masked_or_empty_sf(getattr(row, "siliconflow_api_key", None) or "") else "",
        siliconflow_base_url=sf_base,
    )


# --- CRUD ---
@router.get("", response_model=List[KBOut])
async def list_kbs(
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.id))
    rows = r.scalars().all()
    return [
        KBOut(
            id=x.id,
            name=x.name,
            description=x.description,
            kg_status=x.kg_status,
            kg_progress=x.kg_progress,
            kg_error=x.kg_error,
            created_at=x.created_at.isoformat() if x.created_at else None,
        )
        for x in rows
    ]


@router.post("", response_model=KBOut)
async def create_kb(
    body: KBCreate,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    kb = KnowledgeBase(name=body.name, description=body.description)
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return KBOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        kg_status=kb.kg_status,
        kg_progress=kb.kg_progress,
        kg_error=kb.kg_error,
        created_at=kb.created_at.isoformat() if kb.created_at else None,
    )


@router.patch("/{kb_id}", response_model=KBOut)
async def update_kb(
    kb_id: int,
    body: KBUpdate,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = r.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "知识库不存在")
    if body.name is not None:
        kb.name = body.name
    if body.description is not None:
        kb.description = body.description
    await db.flush()
    await db.refresh(kb)
    return KBOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        kg_status=kb.kg_status,
        kg_progress=kb.kg_progress,
        kg_error=kb.kg_error,
        created_at=kb.created_at.isoformat() if kb.created_at else None,
    )


@router.get("/{kb_id}/status")
async def get_kb_status(
    kb_id: int,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    """轮询构建进度：优先返回内存中的 building 状态，否则返回库里的 status。"""
    if kb_id in _build_status:
        return _build_status[kb_id]
    r = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = r.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "知识库不存在")
    return {
        "progress": kb.kg_progress,
        "status": kb.kg_status,
        "error": kb.kg_error,
    }


@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: int,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = r.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "知识库不存在")
    docs = (await db.execute(select(Document).where(Document.kb_id == kb_id))).scalars().all()
    for d in docs:
        await db.delete(d)
    await db.delete(kb)
    lightrag_service.delete_kb_rag(kb_id)
    try:
        neo4j_kg_service.delete_workspace(kb_id)
    except Exception:
        pass
    _build_status.pop(kb_id, None)
    return {"ok": True}


# --- Documents ---
@router.get("/{kb_id}/documents", response_model=List[DocOut])
async def list_documents(
    kb_id: int,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    if not r.scalar_one_or_none():
        raise HTTPException(404, "知识库不存在")
    r = await db.execute(select(Document).where(Document.kb_id == kb_id).order_by(Document.id))
    rows = r.scalars().all()
    return [
        DocOut(
            id=x.id,
            kb_id=x.kb_id,
            filename=x.filename,
            file_type=x.file_type,
            status=x.status,
            build_status=getattr(x, "build_status", "pending") or "pending",
            created_at=x.created_at.isoformat() if x.created_at else None,
        )
        for x in rows
    ]


@router.post("/{kb_id}/upload")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    """仅上传并保存文件，不自动构建。上传后文档状态为「未参与构建」，需点击「构建知识图谱」后才会参与。"""
    r = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = r.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "知识库不存在")

    name = file.filename or "file"
    ext = Path(name).suffix.lower()
    if ext not in (".txt", ".pdf", ".docx", ".doc"):
        raise HTTPException(400, "仅支持 .txt / .pdf / .docx / .doc")

    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    import uuid
    stem = uuid.uuid4().hex[:16]
    save_path = settings.UPLOAD_DIR / f"{stem}{ext}"
    content = await file.read()
    save_path.write_bytes(content)

    doc = Document(
        kb_id=kb_id,
        filename=name,
        file_path=str(save_path),
        file_type=ext,
        file_size=len(content),
        status="uploaded",
        build_status="pending",
    )
    db.add(doc)
    await db.flush()
    return {"message": "上传成功，请点击「构建知识图谱」参与构建", "doc_id": doc.id}


@router.post("/{kb_id}/build")
async def build_knowledge_graph(
    kb_id: int,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    """对当前知识库中所有「未参与构建」的文档执行 LightRAG 构建。需先配置 LightRAG（API Key 等）。"""
    r = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = r.scalar_one_or_none()
    if not kb:
        raise HTTPException(404, "知识库不存在")

    r = await db.execute(select(Document).where(Document.kb_id == kb_id, Document.build_status == "pending"))
    pending = r.scalars().all()
    if not pending:
        return {"message": "没有待构建的文档", "built": 0}

    # 仅三种：硅基流动（默认）> 本地 Ollama > Gemini API
    import os
    rcfg = await db.execute(select(RAGConfig).limit(1))
    row = rcfg.scalar_one_or_none()
    use_sf = bool(getattr(row, "use_siliconflow", 1) if row else 1)
    use_ollama = bool(getattr(row, "use_ollama", 0) if row else 0)
    sf_key = (getattr(row, "siliconflow_api_key", None) or "").strip()
    if sf_key == _MASKED_API_KEY or not sf_key:
        sf_key = (getattr(settings, "SILICONFLOW_API_KEY", "") or os.getenv("SILICONFLOW_API_KEY", "")).strip()

    if use_sf and sf_key:
        base = (getattr(row, "siliconflow_base_url", None) or "").strip() or getattr(settings, "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
        config = {
            "use_siliconflow": True,
            "siliconflow_api_key": sf_key,
            "siliconflow_base_url": base.rstrip("/"),
            "llm_model": (row.llm_model or "").strip() or getattr(settings, "SILICONFLOW_LLM_MODEL", "Qwen/Qwen3-8B"),
            "embed_model": (row.embed_model or "").strip() or getattr(settings, "SILICONFLOW_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B"),
        }
    elif use_ollama:
        ollama_base = (getattr(row, "ollama_base_url", None) or "").strip() or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        config = {
            "use_ollama": True,
            "ollama_base_url": ollama_base,
            "llm_model": (row.llm_model or "").strip() or os.getenv("OLLAMA_LLM_MODEL", "qwen3:8b"),
            "embed_model": (row.embed_model or "").strip() or getattr(settings, "LOCAL_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B"),
        }
    else:
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        api_key = _effective_api_key(row.api_key if row else None, env_key)
        if not api_key:
            raise HTTPException(
                400,
                "请先在「LightRAG 配置」中选择 Gemini 并保存 API Key，或在 .env 中配置 GEMINI_API_KEY。",
            )
        config = {
            "use_ollama": False,
            "use_siliconflow": False,
            "api_key": api_key,
            "llm_model": (row.llm_model or "").strip() or "gemini-2.0-flash",
            "embed_model": (row.embed_model or "").strip() or "gemini-embedding-001",
        }
    # 构建前清除该知识库的 RAG 缓存，确保使用本次的 config（含最新 API Key）
    lightrag_service._rag_instances.pop(kb_id, None)

    texts = []
    for doc in pending:
        try:
            t = _extract_text(Path(doc.file_path), doc.file_type)
            if t and t.strip():
                texts.append(t.strip())
        except Exception as e:
            doc.build_status = "failed"
            doc.status = "failed"
            kb.kg_status = "failed"
            kb.kg_error = f"解析失败 {doc.filename}: {e}"
            await db.flush()
            raise HTTPException(400, f"解析文档失败 {doc.filename}: {e}")

    if not texts:
        return {"message": "没有可提取的文本内容", "built": 0}

    combined_text = "\n\n".join(texts)
    for doc in pending:
        doc.build_status = "building"
    kb.kg_status = "building"
    kb.kg_progress = 0
    kb.kg_error = None
    await db.flush()

    _update_build_status(kb_id, 0, "building", None)
    asyncio.create_task(_run_build_async(kb_id, combined_text, config=config))
    return {"message": "已开始构建知识图谱", "pending_count": len(pending)}


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(
    kb_id: int,
    doc_id: int,
    user=Depends(require_teacher_or_ta),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(Document).where(Document.id == doc_id, Document.kb_id == kb_id))
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")
    await db.delete(doc)
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    return {"ok": True}


# --- 知识图谱：图、节点、路径（Neo4j）---
@router.get("/{kb_id}/graph")
async def get_graph(
    kb_id: int,
    limit: int = 500,
    user=Depends(require_teacher_or_ta),
):
    """获取知识图谱数据，用于前端可视化。从 Neo4j 读取；Neo4j 不可用时返回空图。"""
    try:
        return neo4j_kg_service.get_graph(kb_id, limit=limit)
    except Exception as e:
        err = str(e).lower()
        if "connection refused" in err or "database not available" in err or "service unavailable" in err:
            return {"nodes": [], "edges": []}
        raise HTTPException(502, f"Neo4j 查询失败: {e}")


@router.get("/{kb_id}/nodes")
async def get_nodes(
    kb_id: int,
    keyword: Optional[str] = None,
    limit: int = 50,
    user=Depends(require_teacher_or_ta),
):
    """查询知识图谱节点，支持关键词。"""
    try:
        return {"nodes": neo4j_kg_service.query_nodes(kb_id, keyword=keyword, limit=limit)}
    except Exception as e:
        err = str(e).lower()
        if "connection refused" in err or "database not available" in err or "service unavailable" in err:
            return {"nodes": []}
        raise HTTPException(502, f"Neo4j 查询失败: {e}")


@router.get("/{kb_id}/path")
async def get_path(
    kb_id: int,
    from_name: str,
    to_name: str,
    max_depth: int = 10,
    user=Depends(require_teacher_or_ta),
):
    """查询两节点间最短路径（如：从当前知识点到目标知识点）。"""
    if not from_name.strip() or not to_name.strip():
        raise HTTPException(400, "请提供 from_name 与 to_name")
    try:
        return neo4j_kg_service.query_path(kb_id, from_name.strip(), to_name.strip(), max_depth=max_depth)
    except Exception as e:
        raise HTTPException(502, f"Neo4j 查询失败: {e}")
