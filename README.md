# RAG 学习管理系统

完整的 RAG（检索增强生成）后台管理系统，支持 API/本地大模型、知识库管理、自定义 Prompt，提供 OpenAI 兼容接口。

## 功能特性

- **登录鉴权**：教师、助教、学生角色，登录/注册/忘记密码
- **助教管理**：仅教师可增删助教
- **模型配置**：API（OpenAI/DeepSeek 等）或本地模型，ModelScope 下载基座模型
- **RAG 知识库**：PDF/Word/TXT 文档导入、向量检索
- **自定义 Prompt**：初始化系统提示词
- **OpenAI 兼容接口**：`/v1/chat/completions` 供外部调用

## 环境要求

- Python 3.10+
- Node.js 18+
- Conda

## 快速开始

### 1. 创建 Conda 环境并安装依赖

```bash
# 方式一：使用 environment.yml（推荐）
conda env create -f environment.yml
conda activate learning-sys

# 方式二：手动创建
conda create -n learning-sys python=3.10 -y
conda activate learning-sys
pip install -r requirements.txt
```

> 首次安装 RAG 相关依赖（chromadb、sentence-transformers）可能需要 5–10 分钟

### 2. 初始化数据库

```bash
cd backend
python init_db.py
```

默认教师账号：`admin` / `admin123`

### 3. 启动后端

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 安装并启动前端

```bash
npm install
npm run dev
```

访问 http://localhost:5173

## 项目结构

```
learning-sys-manage/
├── backend/           # Python FastAPI 后端
│   ├── api/           # 路由
│   ├── models/        # 数据库模型
│   ├── services/      # 业务服务
│   ├── main.py
│   └── init_db.py
├── src/               # Vue 前端
│   ├── views/         # 页面
│   ├── api/           # 接口
│   └── stores/        # Pinia 状态
├── requirements.txt
└── package.json
```

## API 文档

启动后端后访问：http://localhost:8000/docs

## OpenAI 兼容接口

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"default","messages":[{"role":"user","content":"你好"}]}'
```

## 本地模型说明

使用本地模型时，需要先启动兼容 OpenAI API 的推理服务（如 vLLM、ollama、sglang 等），在模型配置中填写服务地址（如 `http://127.0.0.1:8000/v1`）和模型名称。

通过 ModelScope 下载的模型可放到 `./models` 目录，然后使用相应推理框架加载。

## LightRAG + 知识图谱（Gemini + Neo4j）

知识库的「构建知识图谱」使用 LightRAG，**仅使用 Gemini API**（LLM + Embedding），图数据存储在 **Neo4j**。配置见 [**docs/CONFIG.md**](docs/CONFIG.md)，环境变量示例见 **.env.example**。
