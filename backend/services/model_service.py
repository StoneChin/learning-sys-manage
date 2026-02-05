"""模型管理服务 - API/本地模型、ModelScope 下载"""
import asyncio
import os
from pathlib import Path
from typing import List

from config import settings


def get_local_models() -> List[str]:
    """获取本地模型目录下的模型名称列表"""
    base = Path(settings.LOCAL_MODELS_DIR)
    if not base.exists():
        return []
    models = []
    for item in base.iterdir():
        if item.is_dir():
            # 检查是否有常见模型文件
            if (item / "config.json").exists() or (item / "config.yaml").exists():
                models.append(item.name)
            else:
                models.append(item.name)
    return sorted(models)


async def download_from_modelscope(model_id: str, save_dir: str) -> dict:
    """通过 ModelScope 下载模型到指定目录"""
    try:
        from modelscope import snapshot_download
    except ImportError:
        return {"success": False, "error": "请安装 modelscope: pip install modelscope"}

    def _download():
        path = snapshot_download(model_id, cache_dir=save_dir)
        return path

    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(None, _download)
    return {"success": True, "path": str(path)}


def get_modelscope_popular_models() -> List[dict]:
    """返回常用 ModelScope 模型列表供选择"""
    return [
        {"id": "Qwen/Qwen2-0.5B", "name": "Qwen2-0.5B"},
        {"id": "Qwen/Qwen2-1.5B", "name": "Qwen2-1.5B"},
        {"id": "Qwen/Qwen2-7B", "name": "Qwen2-7B"},
        {"id": "deepseek-ai/DeepSeek-V2-Lite-Chat", "name": "DeepSeek-V2-Lite-Chat"},
        {"id": "THUDM/glm-4-9b-chat", "name": "GLM-4-9B-Chat"},
        {"id": "internlm/internlm2_5-7b-chat", "name": "InternLM2.5-7B-Chat"},
    ]
