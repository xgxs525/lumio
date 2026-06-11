# lumio

序光是一个 AI 表格协作与办公工具平台，已完成从单体 Jinja2 原型向现代全栈架构的第一阶段迁移。

## 技术栈

### 后端
- Python + FastAPI
- PostgreSQL（SQLAlchemy async）
- Redis
- Celery（异步任务）
- OSS / 本地存储抽象层
- AI Gateway（统一大模型接入）

### 前端
- Next.js + React + TypeScript
- Tailwind CSS
- shadcn/ui 风格组件

## 目录结构

```text
backend/          # 新后端 API 服务（当前主入口）
frontend/         # Next.js 前端（当前主入口）
app.py            # 旧版单体服务（已废弃，仅保留参考）
excel_splitter.py # 表格拆分核心逻辑（被新旧后端共用）
templates/        # 旧版 HTML 模板（已废弃，仅保留参考）
static/           # 旧版静态资源（已废弃，仅保留参考）
docker-compose.yml # 基础设施编排（PostgreSQL + Redis，仍在使用）
```

## 本地启动

### 1. 启动基础设施

```powershell
docker compose up -d
```

### 2. 启动后端 API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="I:\lumio\backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动 Celery Worker

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="I:\lumio\backend"
celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo
```

### 4. 启动前端

```powershell
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

访问：

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/docs
- 旧版原型（可选）：`python app.py` → http://localhost:5000

## 环境变量

复制根目录 `.env.example` 并按需修改：

- `DATABASE_URL`：PostgreSQL 连接
- `REDIS_URL` / `CELERY_*`：任务队列
- `STORAGE_BACKEND`：`local` 或 `oss`
- `AI_GATEWAY_API_KEY`：AI 模型密钥

前端复制 `frontend/.env.local.example` 为 `.env.local`。

## API 概览

| 模块 | 路径 |
|------|------|
| 健康检查 | `GET /api/v1/health` |
| 文件上传 | `POST /api/v1/files/upload` |
| 列名读取 | `POST /api/v1/files/columns` |
| 拆分预览 | `POST /api/v1/tasks/preview` |
| 提交拆分 | `POST /api/v1/tasks/split` |
| 任务状态 | `GET /api/v1/tasks/{id}` |
| 模板列表 | `GET /api/v1/templates` |
| AI 对话 | `POST /api/v1/ai/chat` |

## 迁移说明

当前状态：

- 核心业务（上传、预览、拆分、任务查询、AI 对话、模板）已迁移到新后端
- 前端核心页面（首页、工具中心、拆分、AI、模板、登录、价格）已用 Next.js 重建
- 账号鉴权、云盘、知识库等仍为下一阶段待接入能力

### 关于旧版文件

以下文件/目录属于旧版单体架构，已停止维护，仅作为迁移参考保留：

| 文件/目录 | 状态 | 说明 |
|-----------|------|------|
| `app.py` | 已废弃 | 旧版 FastAPI 单体服务入口，功能已由 `backend/` 接管 |
| `templates/` | 已废弃 | 旧版 Jinja2 HTML 模板，页面已由 `frontend/` 重建 |
| `static/` | 已废弃 | 旧版静态资源（CSS/JS），对应新版资源在 `frontend/public/` 和 `frontend/src/app/` 中 |

> 注意：`excel_splitter.py` 虽然位于根目录，但仍是**核心逻辑文件**，被新后端服务直接依赖调用，不属于废弃文件。
