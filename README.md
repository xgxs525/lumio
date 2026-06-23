# 序光 (XuGuang) — AI 原生办公平台

序光是一站式 AI 办公平台，集成智能知识库、文件理解、在线文档协作、团队管理与多模型 AI 对话能力。项目采用前后端分离架构：FastAPI 后端 + Next.js 前端。

## 项目结构

```
lumio/
├── backend/                    # FastAPI 后端 (Python)
│   ├── app/
│   │   ├── api/routes/         # API 路由 (22 个模块)
│   │   ├── core/               # 配置、数据库、安全
│   │   ├── models/             # SQLAlchemy ORM 模型 (13 个)
│   │   ├── schemas/            # Pydantic 数据校验
│   │   ├── services/           # 业务逻辑 (AI、存储、计费)
│   │   └── tasks/              # Celery 异步任务
│   ├── alembic/                # 数据库迁移
│   └── requirements.txt
│
├── lumio-frontend/             # Next.js 前端 (TypeScript)
│   └── src/
│       ├── app/                # App Router 页面 (~35 个路由)
│       ├── components/         # 共享组件 (UI、布局、业务)
│       ├── lib/                # API 客户端、认证工具
│       └── globals.css
│
├── docker-compose.yml          # Docker 编排
├── config.yaml                 # 应用配置文件
└── README.md
```

## 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| Python 3.13 + FastAPI | API 框架 |
| PostgreSQL | 主数据库 |
| SQLAlchemy (Async) | ORM |
| Alembic | 数据库迁移 |
| Redis | 缓存 / 队列 |
| Celery | 异步任务 |
| pgvector | 向量存储 |
| OpenAI-compatible API | AI & Embedding 网关 |

### 前端
| 技术 | 用途 |
|------|------|
| Next.js 15 (App Router) | 框架 |
| TypeScript | 类型安全 |
| Tailwind CSS | 样式 |
| TipTap | 富文本编辑器 |
| Lucide React | 图标 |

## 环境依赖

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- (可选) pgvector 扩展

## 快速启动

### 1. 克隆仓库

```bash
git clone <repo-url>
cd lumio
```

### 2. 后端启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 配置环境变量 (复制 .env.example 为 .env 并填写)
copy .env.example .env

# 启动开发服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

或使用提供的脚本：
```powershell
.\run-api.ps1
```

### 3. 前端启动

```powershell
cd lumio-frontend
npm install
npm run dev
```

### 4. 访问

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:3000 |
| API 接口 | http://localhost:8000/api/v1 |
| Swagger 文档 | http://localhost:8000/docs |

## 环境变量

在 `backend/` 下创建 `.env` 文件：

```env
APP_NAME=序光
APP_ENV=development
DEBUG=true
API_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000

DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/lumio
REDIS_URL=redis://localhost:6379/0

AI_GATEWAY_BASE_URL=https://api.openai.com/v1
AI_GATEWAY_API_KEY=sk-xxx
AI_GATEWAY_MODEL=gpt-4o-mini

EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=128

STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./storage

SECRET_KEY=change-me-in-production
```

## API 接口说明

API 基础路径：`/api/v1`

### 核心模块

| 模块 | 路径前缀 | 说明 |
|------|---------|------|
| 认证 | `/auth` | 注册、登录、退出、Token 管理 |
| 云盘 | `/drive` | 文件/文件夹 CRUD、上传、预览、下载 |
| 在线文档 | `/documents` | 文档创建、编辑、版本、导出 |
| 知识库 | `/knowledge-bases` | 知识库管理、资料添加、向量索引、问答 |
| 文件 AI | `/file-ai` | 文件解析、分块、向量化、总结、问答 |
| AI 对话 | `/ai` | 多模型对话、会话管理 |
| 团队 | `/team` | 成员、部门、角色、审计日志 |
| 计费 | `/billing` | 套餐、订单、支付 |
| 用量 | `/usage` | 资源用量统计 |
| 任务 | `/jobs` | 异步任务管理 |
| 管理 | `/admin` | 后台管理 |
| 模板 | `/templates` | 模板中心 |
| 分享 | `/share` | 文件/文档分享 |

> 完整接口文档访问 `http://localhost:8000/docs` (Swagger UI)

### 知识库核心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/knowledge-bases` | 获取知识库列表 |
| POST | `/knowledge-bases` | 创建知识库 |
| GET | `/knowledge-bases/{id}` | 获取知识库详情 |
| PATCH | `/knowledge-bases/{id}` | 更新知识库 |
| DELETE | `/knowledge-bases/{id}` | 删除知识库 |
| GET | `/knowledge-bases/{id}/sources` | 获取资料来源列表 |
| POST | `/knowledge-bases/{id}/sources` | 添加资料来源 (文件/文档/链接/文本/手动) |
| DELETE | `/knowledge-bases/{id}/sources/{sid}` | 删除资料来源 |
| POST | `/knowledge-bases/{id}/ask` | 知识库问答 |
| POST | `/knowledge-bases/{id}/sync` | 同步知识库索引 |

## Docker 部署

```bash
# 启动全部服务
docker-compose up -d

# 仅启动数据库和 Redis
docker-compose up -d postgres redis
```

`docker-compose.yml` 包含 PostgreSQL、Redis 及 API 服务定义。

## 数据库迁移

```powershell
cd backend
alembic upgrade head
```

服务启动时自动执行兼容迁移并创建缺失表（`core/schema_compat.py`）。

## 主要功能模块

| 功能 | 说明 |
|------|------|
| 🧠 智能知识库 | 支持文件/文档/链接/文本多源资料，自动分块与向量索引，基于资料的 AI 问答 |
| 📄 文件理解 | PDF/Word/Excel/PPT/TXT/Markdown 解析，表格拆分，AI 总结与问答 |
| ✍️ 在线文档 | 块编辑器，支持 H1-H3、列表、表格、图片、代码块、公式，AI 写作辅助 |
| 💬 AI 对话 | 多模型支持 (GPT/Claude/DeepSeek)，会话管理，文件附件分析 |
| ☁️ 云盘 | 文件上传/下载/预览，文件夹管理，回收站，分享链接 |
| 👥 团队协作 | 成员邀请、部门管理、角色权限、操作审计 |
| 💰 计费系统 | 套餐订阅、订单管理、用量统计、支付集成 |
| 📊 后台管理 | 用户、工作空间、存储、订单管理面板 |

## 前端路由表

| 路径 | 页面 |
|------|------|
| `/` | 首页 |
| `/login` / `/register` | 登录 / 注册 |
| `/workspace` | 工作空间首页 |
| `/drive` | 云盘文件管理 |
| `/knowledge` | 知识库列表 |
| `/knowledge/{id}` | 知识库详情 |
| `/knowledge/{id}/add-source` | 添加资料工作台 |
| `/ai` | AI 对话 |
| `/documents` | 在线文档 |
| `/settings` | 个人设置 |
| `/admin` | 后台管理 |
| `/billing` | 计费中心 |
| `/team` | 团队管理 |
| `/tasks` | 任务中心 |
| `/templates` | 模板中心 |
| `/tools` | 工具集 |

## 开发指南

```powershell
# 后端语法检查
python -m compileall backend\app

# 前端类型检查
cd lumio-frontend && npx tsc --noEmit

# 数据库迁移
cd backend && alembic upgrade head

# 种子数据
python backend\seed_models.py
```

## 生产部署建议

- PostgreSQL 配置连接池与定期备份
- Redis 承载会话、限流、队列与缓存
- 文件存储切换至 OSS/S3，使用签名 URL
- AI/Embedding/支付等外部服务通过环境变量配置
- 长任务使用 Celery Worker，不依赖 FastAPI BackgroundTasks
- 接入日志收集、性能监控与错误告警
- 启用 HTTPS 与 CORS 白名单

## License

MIT
