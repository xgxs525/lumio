# 序光后端

序光后端是 AI 原生办公平台的 API 服务，基于 FastAPI、PostgreSQL、SQLAlchemy、Alembic 和异步任务能力构建，提供用户体系、工作空间、云盘、在线文档、知识库、文件 AI、任务中心、团队协作、用量统计、商业化和后台管理接口。

## 命名约定

对外产品名称统一为“序光”，接口返回给用户的产品名通过 `APP_NAME=序光` 控制。仓库名、数据库名、本地目录名等技术标识按部署环境保留，避免影响连接、迁移和自动化脚本。

## 技术栈

- Python + FastAPI
- PostgreSQL
- SQLAlchemy Async ORM
- Alembic 数据库迁移
- pgvector 向量扩展
- Redis / Celery 预留
- OpenAI-compatible AI Gateway / Embedding Gateway

## 目录结构

```text
backend/
  app/
    api/               # API 路由
    core/              # 配置、数据库、认证、安全
    models/            # ORM 模型
    schemas/           # Pydantic Schema
    services/          # 文件、AI、支付、存储等服务
  alembic/             # 数据库迁移
```

## 快速启动

```powershell
cd I:\lumio
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

默认 API 地址：

```text
http://localhost:8000/api/v1
```

接口文档：

```text
http://localhost:8000/docs
```

## 环境变量

开发环境可创建 `.env`：

```env
APP_NAME=序光
APP_ENV=development
DEBUG=true
API_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

DATABASE_URL=postgresql+asyncpg://postgres:Xg022335@localhost:5432/lumio
REDIS_URL=redis://localhost:6379/0

AI_GATEWAY_BASE_URL=https://api.openai.com/v1
AI_GATEWAY_API_KEY=
AI_GATEWAY_MODEL=gpt-4o-mini

EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=128

STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./storage

SECRET_KEY=change-me-in-production
```

## 数据库迁移

```powershell
alembic upgrade head
```

服务启动时也会执行兼容迁移并创建缺失表，便于本地开发。

## 主要模块

- `auth`：注册、登录、当前用户、退出登录
- `drive`：云盘、文件夹、上传、预览、下载、删除
- `documents`：在线文档、AI 写作、导出
- `knowledge`：知识库、来源、成员、问答、引用
- `file_ai`：文件解析、切片、向量化、问答、总结
- `jobs`：异步任务与任务状态
- `team`：成员、部门、角色、审计日志
- `billing`：套餐、订单、支付、额度
- `usage`：用量统计
- `admin`：后台管理
- `templates`：模板中心
- `share`：文件和文档分享

## 常用命令

```powershell
python -m compileall backend\app       # Python 语法检查
uvicorn backend.app.main:app --reload  # 本地开发服务
alembic upgrade head                   # 应用迁移
```

## 生产部署建议

- PostgreSQL 开启连接池和备份策略。
- Redis 承载验证码、限流、任务队列和缓存。
- 文件存储切换到 OSS / S3，并使用签名 URL。
- AI、Embedding、短信、邮件、支付等外部服务通过环境变量配置。
- 长任务使用 Celery Worker 或队列服务，不建议只依赖 FastAPI BackgroundTasks。
- 接入日志、监控、错误告警和审计留痕。
