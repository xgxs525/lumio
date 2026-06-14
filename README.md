# Lumio 序光后端

Lumio 序光是一个 AI 原生办公工作空间后端服务，提供用户体系、工作空间、云盘、在线文档、知识库、文件 AI、任务中心、团队协作、用量统计、商业化和后台管理能力。

前端已经拆分到独立项目：`I:\lumio-frontend`。

## 技术栈

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy Async + Alembic
- PostgreSQL，支持 pgvector 扩展
- Redis，用于后续限流、验证码、任务队列和缓存
- 本地文件存储，预留 OSS / S3 接入
- OpenAI-compatible AI Gateway，未配置时使用本地降级逻辑

## 目录结构

```text
backend/
  app/
    api/routes/        # API 路由
    core/              # 配置、安全、兼容层
    models/            # SQLAlchemy 数据模型
    schemas/           # Pydantic 入参和出参
    services/          # 业务服务
    utils/             # 文件、解析等工具
    main.py            # FastAPI 入口
  alembic/             # 数据库迁移
  alembic.ini
  requirements.txt
docker-compose.yml     # PostgreSQL + Redis 基础环境
uploads/               # 本地上传目录，运行期生成，不提交
outputs/               # 处理结果目录，运行期生成，不提交
```

## 快速启动

1. 启动基础设施：

```powershell
cd I:\lumio
docker compose up -d
```

2. 准备环境变量：

```powershell
Copy-Item .env.example .env
```

3. 安装依赖：

```powershell
I:\lumio\.venv\Scripts\python.exe -m pip install -r I:\lumio\backend\requirements.txt
```

4. 执行数据库迁移：

```powershell
cd I:\lumio\backend
I:\lumio\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

5. 启动后端：

```powershell
cd I:\lumio\backend
$env:PYTHONPATH = "I:\lumio\backend"
I:\lumio\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

接口文档默认地址：

- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 关键环境变量

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/lumio
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me

STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=backend/storage

AI_GATEWAY_BASE_URL=
AI_GATEWAY_API_KEY=
AI_MODEL=
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
EMBEDDING_DIMENSION=1536

OSS_ENDPOINT=
OSS_BUCKET=
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_PUBLIC_BASE_URL=

PAYMENT_PROVIDER=mock
PAYMENT_WEBHOOK_SECRET=
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
SMS_PROVIDER=
SMS_ACCESS_KEY=
```

不要提交 `.env`、上传文件、处理结果和本地存储目录。

## API 模块

当前后端主要模块：

- `/api/v1/auth`：注册、登录、当前用户、资料和密码
- `/api/v1/users`：用户资料扩展
- `/api/v1/workspaces`：工作空间
- `/api/v1/drive`、`/api/v1/folders`：云盘文件和文件夹
- `/api/v1/documents`：在线文档、AI 写作和导出
- `/api/v1/knowledge-bases`：知识库、来源、问答和引用
- `/api/v1/file-ai`：文件解析、切片、embedding、问答、总结和处理任务
- `/api/v1/chat`：AI 会话
- `/api/v1/jobs`、`/api/v1/tasks`：异步任务和任务中心
- `/api/v1/team`：成员、部门、角色、邀请和审计日志
- `/api/v1/billing`：套餐、订单、支付和订阅
- `/api/v1/usage`：存储、AI 调用和团队用量
- `/api/v1/admin`：运营后台管理
- `/api/v1/templates`：模板上传、列表和下载
- `/api/v1/share`：文件和文档分享

## 验证命令

```powershell
cd I:\lumio\backend
I:\lumio\.venv\Scripts\python.exe -m compileall app -q
```

如果需要检查应用是否能导入：

```powershell
cd I:\lumio\backend
$env:PYTHONPATH = "I:\lumio\backend"
I:\lumio\.venv\Scripts\python.exe -c "from app.main import app; print(len(app.routes))"
```

## 生产部署建议

- 使用 PostgreSQL + pgvector 存储向量，避免仅依赖内存检索。
- 使用 Redis + Celery/RQ 承接长任务，例如 OCR、文档解析、批量处理和 embedding。
- 使用 OSS/S3 存储上传文件和处理结果，并通过签名 URL 访问。
- 接入真实支付网关后，必须校验支付回调签名。
- 接入短信、邮件、AI 网关和 OCR 服务时，请只通过环境变量配置密钥。
- 对外部署建议使用 Nginx / API Gateway，并启用 HTTPS、访问日志、限流和监控。
