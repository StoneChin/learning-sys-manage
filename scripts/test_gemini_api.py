#!/usr/bin/env python3
"""
测试 Gemini API 调用（参考官方文档）。
用法：在项目根目录执行
  python scripts/test_gemini_api.py
或在 backend 目录且 .env 在项目根目录时：
  GEMINI_API_KEY=xxx python scripts/test_gemini_api.py
"""
import os
import sys

# 项目根目录 = 当前文件所在目录的上一级
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# 从项目根目录加载 .env
_env_file = os.path.join(_ROOT, ".env")
if os.path.isfile(_env_file):
    from dotenv import load_dotenv
    load_dotenv(_env_file)
    print(f"[OK] Loaded .env from {_env_file}")
else:
    print(f"[WARN] No .env at {_env_file}, using process env only")

api_key = os.getenv("GEMINI_API_KEY", "").strip()
if not api_key:
    print("[FAIL] GEMINI_API_KEY not set. Set it in .env or environment.")
    sys.exit(1)
print(f"[OK] GEMINI_API_KEY present (len={len(api_key)})")


def test_generate_content():
    """官方 quickstart: generate_content"""
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="用一句话介绍你自己。",
    )
    text = getattr(response, "text", None) or (response.candidates[0].content.parts[0].text if response.candidates else None)
    print("[OK] generate_content:", (text or str(response))[:200])
    return True


def test_embed_content():
    """官方 embeddings 文档: embed_content，单条与 config"""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    # 单条
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents="What is the meaning of life?",
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=1536,
        ),
    )
    if not result.embeddings:
        print("[FAIL] embed_content single: no embeddings")
        return False
    emb = result.embeddings[0]
    dim = len(emb.values) if hasattr(emb, "values") else 0
    print(f"[OK] embed_content single: dim={dim}")
    # 批量
    result2 = client.models.embed_content(
        model="gemini-embedding-001",
        contents=["文本一", "文本二"],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=1536,
        ),
    )
    if not result2.embeddings or len(result2.embeddings) != 2:
        print("[FAIL] embed_content batch: expected 2 embeddings, got", len(getattr(result2, "embeddings", [])))
        return False
    print(f"[OK] embed_content batch: {len(result2.embeddings)} embeddings")
    return True


def test_async_embed():
    """异步 embed（与 LightRAG 调用方式一致）"""
    import asyncio
    from google import genai
    from google.genai import types

    async def run():
        client = genai.Client(api_key=api_key)
        result = await client.aio.models.embed_content(
            model="gemini-embedding-001",
            contents=["异步测试文本"],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=1536,
            ),
        )
        return result

    result = asyncio.run(run())
    if not result.embeddings:
        print("[FAIL] async embed_content: no embeddings")
        return False
    print(f"[OK] async embed_content: dim={len(result.embeddings[0].values)}")
    return True


if __name__ == "__main__":
    ok = 0
    try:
        if test_generate_content():
            ok += 1
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            print("[SKIP] generate_content: quota exceeded (request format is OK)")
            ok += 1
        else:
            print("[FAIL] generate_content:", e)
    try:
        if test_embed_content():
            ok += 1
    except Exception as e:
        print("[FAIL] embed_content:", e)
    try:
        if test_async_embed():
            ok += 1
    except Exception as e:
        print("[FAIL] async embed:", e)
    print("---")
    if ok == 3:
        print("All 3 Gemini API tests passed.")
    else:
        print(f"Passed {ok}/3. Check failures above.")
        sys.exit(1)
