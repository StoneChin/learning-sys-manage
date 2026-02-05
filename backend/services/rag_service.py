"""RAG 知识库服务 - 文档解析、向量存储、检索"""
import asyncio
import hashlib
import shutil
from pathlib import Path
from typing import List, Optional

from config import settings


def _read_txt(path: Path) -> str:
    for enc in ["utf-8", "gbk", "gb2312"]:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def _read_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_text(path: Path, ext: str) -> str:
    ext = ext.lower()
    if ext == ".txt":
        return _read_txt(path)
    if ext == ".pdf":
        return _read_pdf(path)
    if ext in (".docx", ".doc"):
        return _read_docx(path)
    raise ValueError(f"不支持的文件类型: {ext}")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def _get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return model
    except Exception:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer("all-MiniLM-L6-v2")
            return model
        except Exception as e:
            raise RuntimeError(f"加载 embedding 模型失败: {e}") from e


_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = _get_embedding_model()
    return _embedding_model


def get_chroma_client():
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    persist_dir = str(settings.RAG_DATA_DIR / "chroma")
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False))


def get_collection(kb_id: int):
    client = get_chroma_client()
    name = f"kb_{kb_id}"
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def add_documents_to_kb(kb_id: int, file_path: Path, file_type: str) -> int:
    """解析文档并添加到知识库，返回添加的 chunk 数量"""
    text = _extract_text(file_path, file_type)
    chunks = _chunk_text(text)
    if not chunks:
        return 0
    model = get_embedding_model()
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()
    coll = get_collection(kb_id)
    ids = [hashlib.md5(f"{kb_id}_{i}_{c[:50]}".encode()).hexdigest() for i, c in enumerate(chunks)]
    coll.add(ids=ids, documents=chunks, embeddings=embeddings)
    return len(chunks)


def search_kb(kb_id: int, query: str, top_k: int = 5) -> List[dict]:
    """在知识库中检索相关内容"""
    model = get_embedding_model()
    q_emb = model.encode([query], show_progress_bar=False).tolist()
    coll = get_collection(kb_id)
    res = coll.query(query_embeddings=q_emb, n_results=top_k, include=["documents", "distances"])
    docs = res["documents"][0] if res["documents"] else []
    dists = res["distances"][0] if res["distances"] else []
    return [{"content": d, "distance": dist} for d, dist in zip(docs, dists)]


def delete_kb_vectors(kb_id: int):
    """删除知识库的所有向量"""
    client = get_chroma_client()
    name = f"kb_{kb_id}"
    try:
        client.delete_collection(name)
    except Exception:
        pass
