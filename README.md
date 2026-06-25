# 序光 (XuGuang) — AI 原生办公平台

序光是一站式 AI 办公平台，集成智能知识库、文件理解、在线文档协作、团队管理、视频创作与多模型 AI 对话能力。项目采用前后端分离架构：FastAPI 后端 + Next.js 前端。

## 项目结构

```
lumio/
├── backend/                    # FastAPI 后端 (Python)
│   ├── app/
│   │   ├── api/routes/         # API 路由
│   │   ├── core/               # 配置、数据库、安全
│   │   ├── models/             # SQLAlchemy ORM 模型
│   │   ├── services/           # 业务逻辑 (AI、存储、计费、邮件)
│   │   └── tasks/              # Celery 异步任务
│   ├── alembic/                # 数据库迁移
│   └── requirements.txt
│
├── lumio-frontend/             # Next.js 前端 (TypeScript)
│   └── src/
│       ├── app/                # App Router 页面
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
| SMTP | 邮件发送 |

### 前端
| 技术 | 用途 |
|------|------|
| Next.js 16 (Turbopack) | 框架 |
| TypeScript | 类型安全 |
| Tailwind CSS | 样式 |
| TipTap | 富文本编辑器 |
| Lucide React | 图标 |

## 环境依赖

- Python 3.13
- Node.js 20+
- PostgreSQL 16+
- Redis 7+

## 快速启动

### 1. 克隆仓库

```bash
git clone https://github.com/xgxs525/lumio.git
git clone https://github.com/xgxs525/lumio-frontend.git
```

### 2. 后端启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env

# 启动开发服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

# SMTP 邮件 (可选，开发模式无需配置)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=noreply@xuguang.com
SMTP_FROM_NAME=序光平台
SITE_URL=http://localhost:3000

AI_GATEWAY_BASE_URL=https://api.openai.com/v1
AI_GATEWAY_API_KEY=sk-xxx
AI_GATEWAY_MODEL=gpt-4o-mini

STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./storage

SECRET_KEY=change-me-in-production
```

## API 接口说明

API 基础路径：`/api/v1`

### 核心模块

| 模块 | 路径前缀 | 说明 |
|------|---------|------|
| 认证 | `/auth` | 注册、登录、退出、忘记密码、重置密码、Token 管理 |
| 云盘 | `/drive` | 文件/文件夹 CRUD、上传、预览、下载、回收站、软删除 |
| 文件夹 | `/folders` | 文件夹详情、重命名、移动、删除 |
| 在线文档 | `/documents` | 文档创建、编辑、版本、导出 |
| 知识库 | `/knowledge-bases` | 知识库管理、资料添加、向量索引、问答 |
| 文件 AI | `/file-ai` | 文件解析、分块、向量化、总结、问答 |
| AI 对话 | `/ai` | 多模型对话、会话管理 |
| 视频创作 | `/video` | 视频模型、视频任务创建与管理 |
| 团队 | `/team` | 成员、部门、角色、审计日志 |
| 计费 | `/billing` | 套餐、订单、支付 |
| 用量 | `/usage` | 资源用量统计 |
| 任务 | `/jobs` | 异步任务管理 |
| 管理 | `/admin` | 后台管理 |
| 模板 | `/templates` | 模板中心 |
| 分享 | `/share` | 文件/文档分享 |

> 完整接口文档访问 `http://localhost:8000/docs` (Swagger UI)

## Docker 部署

```bash
docker-compose up -d
```

## 数据库迁移

服务启动时自动执行兼容迁移并创建缺失表（`core/schema_compat.py`）。

## 主要功能模块

| 功能 | 说明 |
|------|------|
| 🔐 用户认证 | 邮箱/手机号注册登录、忘记密码邮件重置、记住登录 |
| 🧠 智能知识库 | 支持文件/文档/链接/文本多源资料，自动分块与向量索引，基于资料的 AI 问答 |
| 📄 文件理解 | PDF/Word/Excel/PPT/TXT/Markdown 解析，表格拆分，AI 总结与问答 |
| ✍️ 在线文档 | 块编辑器，支持 H1-H3、列表、表格、图片、代码块、公式，AI 写作辅助 |
| 💬 AI 对话 | 多模型支持 (GPT/Claude/DeepSeek)，会话管理，文件附件分析 |
| ☁️ 云盘 | 文件上传/下载/预览/编辑，文件夹导航，回收站软删除/恢复，分享链接 |
| 🎬 视频创作 | 接入多种视频生成模型，支持文生视频、图生视频 |
| 👥 团队协作 | 成员邀请、部门管理、角色权限、操作审计 |
| 💰 计费系统 | 套餐订阅、订单管理、用量统计、支付集成 |
| 📊 后台管理 | 用户、工作空间、存储、订单管理面板 |

## 前端路由表

| 路径 | 页面 |
|------|------|
| `/` | 首页 |
| `/login` / `/register` | 登录 / 注册 |
| `/forgot-password` / `/reset-password` | 忘记密码 / 重置密码 |
| `/workspace` | 工作空间首页 |
| `/tasks` | 任务中心 |
| `/models` | 模型广场 |
| `/creation` | 创作空间 |
| `/creation/image` | 图像生成 |
| `/creation/video` | 视频创作 |
| `/drive` | 云盘文件管理 |
| `/drive/folders/{id}` | 文件夹详情 |
| `/drive/files/{id}` | 文件编辑/预览 |
| `/drive/trash` | 回收站 |
| `/knowledge` | 知识库列表 |
| `/knowledge/{id}` | 知识库详情 |
| `/knowledge/{id}/add-source` | 添加资料工作台 |
| `/ai` | AI 对话 |
| `/settings` | 个人设置 |
| `/billing` | 计费中心 |
| `/team` | 团队管理 |
| `/admin` | 后台管理 |

## 2026-06 更新

- 新增用户认证：忘记密码、邮件重置密码流程，SMTP 集成
- 新增云盘文件夹导航与文件编辑器，支持在线编辑文本文件 (Cmd/Ctrl+S 保存)
- 新增回收站：软删除机制，支持恢复和永久删除
- 新增视频创作模块，支持多模型视频生成
- 新增创作空间入口：整合图像生成与视频创作
- 侧边栏优化：精简为核心 6 项（工作台/任务中心/模型广场/创作空间/知识库/云盘）
- 页面 UI 优化：登录/注册输入框缩小、按钮紧凑化
- 后端全局异常处理与错误日志

## License

MIT
