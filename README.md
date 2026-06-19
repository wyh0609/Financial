# ChatFinance - 金融财报智能问答系统

基于大语言模型的金融财报智能分析系统，支持年报问答、投资分析、公司对比、职业分析等功能。目前尚未完成联网功能。

## 功能特性

- **智能问答** — 基于财报文本的检索问答与开放问答，支持流式输出
- **投资分析** — 财务指标提取、雷达图评分、内在价值评估、投资建议生成
- **公司对比** — 多公司财务指标横向对比，含雷达图可视化
- **职业分析** — 基于 MBTI 人格类型的多公司入职建议分析
- **PDF 上传** — 上传年报 PDF 自动解析为文本，纳入知识库
- **多端支持** — Web 端（Vue3）+ 移动端（UniApp）

## 数据集

- **ChatGLM评估挑战赛-金融赛道数据集** — https://modelscope.cn/datasets/modelscope/chatglm_llm_fintech_raw_dataset/summary

## 系统架构

```
用户 (Web / 移动端)
    │
    ▼
Flask Server (端口 5000)
    │
    ├── /api/chat_stream_get      → 智能问答（SSE 流式）
    ├── /api/invest_analysis      → 投资分析（流式）
    ├── /api/compare_companies    → 公司对比
    ├── /api/career_analysis      → 职业分析
    ├── /api/upload_pdf           → PDF 上传解析
    ├── /api/conversations        → 对话管理
    │
    ├── LLM: DeepSeek API / Ollama 本地模型
    ├── 向量库: Weaviate
    ├── 索引库: ElasticSearch
    └── 知识库: 本地财报文本
```

## 核心处理流程

```
用户提问 → 意图识别（开放/检索）
  ├─ 开放问题 → LLM 直接回答
  └─ 检索问题 → 实体提取（公司+年份）→ 匹配知识库 → 上下文检索 → LLM 生成答案
```

## 项目结构

```
ChatFinance/
├── server.py                 # Flask 服务端（API 接口）
├── main.py                   # 核心引擎（问答/分析逻辑）
├── conversation_manager.py   # 对话管理器
├── embedding.py              # 文本向量化
├── pdf_processor.py          # PDF 上传处理
├── pdf_generator.py          # PDF 报告生成
├── web_searcher.py           # 联网搜索模块
├── configs/server.json       # 服务端配置
├── prompts/                  # 提示词模板
│   ├── intent_recognition.py     # 意图识别
│   ├── entity_recognition.py     # 实体提取
│   ├── answer_generation.py      # 答案生成
│   ├── open_question.py          # 开放问题
│   ├── financial_analysis.py     # 财务分析
│   ├── invest_analysis.py        # 投资分析
│   ├── career_analysis.py        # 职业分析
│   ├── web_search_answer.py      # 联网搜索回答
│   ├── relevance_scoring.py      # 相关性评分
│   └── information_extraction.py # 关键信息提取
├── models_server/            # 模型服务
│   └── chatglm2/
│       ├── deepseek_api_client.py  # DeepSeek API 客户端
│       └── ollama_client.py        # Ollama 本地模型客户端
├── database_server/          # 数据库服务
│   ├── elastic_search/db.py      # ElasticSearch 操作
│   └── weaviate/db.py            # Weaviate 向量库操作
├── frontend-vue/             # Web 前端（Vue3 + Vite）
│   └── src/
│       ├── App.vue
│       └── components/       # 聊天/侧边栏/投资分析/公司对比/职业分析
├── uniapp/                   # 移动端（UniApp）
│   └── pages/
│       ├── index/            # 聊天页
│       ├── compare/          # 公司对比页
│       ├── career/           # 职业分析页
│       └── conversations/    # 对话列表页
├── Dockerfile
├── docker-compose.yml        # ElasticSearch + Weaviate
└── requirements.txt
```

## 快速开始

### 1. 环境准备

```bash
# 创建 Python 虚拟环境
conda create -n chatfinance python=3.10
conda activate chatfinance

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

编辑 `configs/server.json`，设置模型路径和服务端口。

在 `main.py` 中配置 LLM 接口：
- **DeepSeek API**：填入 API Key
- **Ollama 本地模型**：确保 Ollama 服务已启动

### 3. 启动数据库（可选）

```bash
docker-compose up -d
```

### 4. 启动服务

```bash
python server.py
```

服务默认运行在 `http://localhost:5000`。

### 5. 启动前端

```bash
# Web 前端
cd frontend-vue
npm install
npm run dev
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask, LangChain, pdfplumber, reportlab |
| LLM | DeepSeek API / Ollama (deepseek-r1) |
| 向量化 | sentence-transformers (text2vec-base-chinese) |
| 数据库 | ElasticSearch, Weaviate |
| Web 前端 | Vue 3, Vite, Marked |
| 移动端 | UniApp (Vue 3) |
| 部署 | Docker, docker-compose |

## License

See [LICENSE](LICENSE)
