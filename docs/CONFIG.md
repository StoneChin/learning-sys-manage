# LightRAG 配置

LightRAG 仅使用 **Gemini API**（LLM + Embedding），参考 [LightRAG 官方](https://github.com/HKUDS/LightRAG) 的 Gemini 用法。

- 在知识库页 **「LightRAG 配置」** 中填写 **Gemini API Key**、LLM 模型（如 `gemini-2.0-flash`）、Embedding 模型（如 `gemini-embedding-001`），或
- 在项目根目录 `.env` 中设置 `GEMINI_API_KEY`，可选 `LIGHTRAG_LLM_MODEL`、`LIGHTRAG_EMBED_MODEL`。

知识图谱存储使用 **Neo4j**，需先启动 Neo4j，并在 `backend/config.py` 或环境变量中配置 `NEO4J_URI`、`NEO4J_USERNAME`、`NEO4J_PASSWORD`、`NEO4J_DATABASE`。
