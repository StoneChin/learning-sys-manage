#!/usr/bin/env python3
"""在项目根目录运行，验证 LightRAG（Gemini API）+ .env 是否正常。

用法：  python scripts/test_lightrag.py

要求：.env 中配置 GEMINI_API_KEY；Neo4j 已启动且 NEO4J_* 已配置。
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_env = ROOT / ".env"
if _env.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env, override=False)
    except ImportError:
        pass

os.chdir(BACKEND)


async def main():
    from services import lightrag_service, neo4j_kg_service

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("错误: 未设置 GEMINI_API_KEY。请在项目根 .env 中配置。")
        sys.exit(1)

    config = {
        "api_key": api_key,
        "llm_model": os.getenv("LIGHTRAG_LLM_MODEL", "gemini-2.0-flash"),
        "embed_model": os.getenv("LIGHTRAG_EMBED_MODEL", "gemini-embedding-001"),
    }
    test_kb_id = 99999
    test_text = "LightRAG 测试段落。知识图谱可以表示实体与关系。"

    print("1. 检查 Neo4j 连接...")
    try:
        neo4j_kg_service.get_graph(test_kb_id, limit=1)
        print("   Neo4j 连接正常。")
    except Exception as e:
        print(f"   Neo4j 未连接或失败: {e}")
        sys.exit(1)

    print("2. 调用 LightRAG 插入文本（Gemini LLM + Embedding）...")
    try:
        await lightrag_service.insert_text(
            test_kb_id,
            test_text,
            config=config,
            on_progress=lambda p, s, *_: print(f"   进度: {p}% {s}"),
        )
        print("   插入成功。")
    except Exception as e:
        print(f"   插入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("3. 调用 LightRAG 检索...")
    try:
        results = await lightrag_service.search_rag(test_kb_id, "知识图谱", top_k=2, config=config)
        print(f"   检索到 {len(results)} 条上下文。")
        if results:
            print("   首条摘要:", (results[0][:80] + "..." if len(results[0]) > 80 else results[0]))
    except Exception as e:
        print(f"   检索失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    try:
        lightrag_service.delete_kb_rag(test_kb_id)
        neo4j_kg_service.delete_workspace(test_kb_id)
    except Exception:
        pass

    print("\nLightRAG（Gemini API）运行正常。")


if __name__ == "__main__":
    asyncio.run(main())
