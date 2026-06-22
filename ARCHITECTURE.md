# 序光 (XUGUANG Lumio) 架构设计需求文档

> 版本：v2.0.0 | 日期：2026-06-22 | 作者：广州序光向上科技有限公司

---

## 目录

1. [产品概述](#1-产品概述)
2. [技术架构总览](#2-技术架构总览)
3. [后端架构](#3-后端架构)
4. [前端架构](#4-前端架构)
5. [数据模型](#5-数据模型)
6. [API 接口设计](#6-api-接口设计)
7. [部署架构](#7-部署架构)
8. [安全设计](#8-安全设计)
9. [前端页面清单](#9-前端页面清单)

---

## 1. 产品概述

### 1.1 产品定位

**序光 (XUGUANG)** 是一个 **AI 原生办公平台**，将云盘、在线文档、知识库和 AI 助手连接起来，帮助团队上传、整理、理解和处理所有办公资料。

### 1.2 品牌文案

| 项目 | 内容 |
|------|------|
| 品牌名 | XUGUANG 序光 |
| Slogan | 让文件、文档与知识自动运转 |
| 定位 | AI 原生办公平台 / 智能工作网络 |
| 核心价值 | 把云盘、在线文档、知识库和 AI 助手连接成一个可协作、可检索、可处理的智能工作空间 |

### 1.3 核心功能域

```
┌─────────────────────────────────────────────────────────────────┐
│                        序光 AI 办公平台                          │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│   文件处理     │   知识管理     │   AI 能力     │   团队协作       │
│               │               │               │                 │
│ • 云盘存储     │ • 知识库创建   │ • AI 对话     │ • 工作空间管理   │
│ • 文件上传/下载 │ • 资料来源登记 │ • 文件问答    │ • 成员/部门管理  │
│ • 在线文档编辑 │ • 向量化切片   │ • 文档总结    │ • 角色/权限控制  │
│ • 表格拆分     │ • 语义检索     │ • 知识库问答   │ • 审计日志       │
│ • 文件解析     │ • 引用追溯     │ • 智能写作    │ • 文件分享       │
│               │               │               │                 │
├───────────────┴───────────────┴───────────────┴─────────────────┤
│                     商业化与运维                                  │
│ • 套餐定价/支付 • 用量统计/额度 • 后台管理 • 企业版后台            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术架构总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              客户端                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │          Next.js 16 (React 19) · TypeScript · Tailwind v4        │    │
│  │              shadcn/ui (Radix UI) · lucide-react                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                            HTTP/REST API                                │
│                                    │                                     │
├────────────────────────────────────┼────────────────────────────────────┤
│                              服务端                                      │
│  ┌────────────────────────────────┼────────────────────────────────┐    │
│  │                    FastAPI (ASGI) · Uvicorn                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │    │
│  │  │ JWT 认证 │  │ CORS 中间件│  │ 请求日志 │  │ 慢请求告警   │    │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │    │
│  └────────────────────────────────┼────────────────────────────────┘    │
│           │                       │              │                       │
│  ┌────────▼────────┐  ┌───────────▼──────────┐  ┌─▼──────────────────┐  │
│  │   Celery Worker │  │  SQLAlchemy 2.0      │  │  AI Gateway        │  │
│  │   (Excel 拆分)  │  │  (asyncpg 异步引擎)   │  │  (OpenAI-compat)   │  │
│  └────────┬────────┘  └───────────┬──────────┘  └──────────┬─────────┘  │
│           │                       │                        │            │
├───────────┼───────────────────────┼────────────────────────┼────────────┤
│                              基础设施                                    │
│  ┌────────▼────────┐  ┌───────────▼──────────┐  ┌──────────▼─────────┐  │
│  │   Redis 7       │  │   PostgreSQL 16       │  │  OpenAI / 兼容 API │  │
│  │  (Docker/Alpine)│  │   + pgvector (可选)   │  │  (外部服务)        │  │
│  └─────────────────┘  └──────────────────────┘  └────────────────────┘  │
│                                                                         │
│  文件存储: 本地文件系统 / 阿里云 OSS (可选)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 后端架构

### 3.1 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | FastAPI | >=0.115.0 | REST API 服务 |
| ASGI 服务器 | Uvicorn | >=0.30.0 | 异步服务运行 |
| ORM | SQLAlchemy 2.0 | >=2.0.36 | 异步数据库操作 |
| 数据库驱动 | asyncpg | >=0.30.0 | PostgreSQL 异步连接 |
| 数据库 | PostgreSQL 16 | - | 主数据存储 |
| 向量扩展 | pgvector | 可选 | Embedding 向量索引 |
| 缓存/消息队列 | Redis 7 (Alpine) | - | Celery Broker + 缓存 |
| 任务队列 | Celery | >=5.4.0 | 异步任务处理 |
| 数据库迁移 | Alembic | >=1.14.0 | Schema 版本管理 |
| 认证 | python-jose (JWT HS256) | - | Token 签发/验证 |
| 密码哈希 | PBKDF2-SHA256 (260K 迭代) | - | 密码安全存储 |
| 文件解析 | openpyxl / pypdf / python-docx | - | 多格式文件解析 |
| AI Gateway | OpenAI-compatible API | - | 可配置的 AI 模型接入 |
| 对象存储 | 阿里云 OSS (可选) | >=2.19.0 | 生产环境文件存储 |

### 3.2 目录结构

```
backend/
├── run_api.py                    # 启动入口
├── app/
│   ├── main.py                   # FastAPI 应用工厂 (lifespan, CORS, 中间件, 路由挂载)
│   ├── core/
│   │   ├── config.py             # Pydantic Settings 配置 (环境变量读取)
│   │   ├── database.py           # SQLAlchemy 异步引擎 + get_db 依赖注入
│   │   └── security.py           # JWT 签发/验证, 密码哈希
│   ├── api/
│   │   ├── router.py             # 总路由汇集 (20个路由模块)
│   │   ├── deps.py               # 依赖注入 (get_session, get_current_user 等)
│   │   └── routes/               # 各模块路由文件 (20个)
│   ├── models/                   # SQLAlchemy ORM 模型 (22个模型, 8个模块)
│   ├── schemas/                  # Pydantic 请求/响应 Schema
│   ├── services/                 # 业务逻辑层
│   ├── tasks/                    # Celery 异步任务
│   └── utils/                    # 工具函数
├── alembic/                      # 数据库迁移脚本
└── storage/                      # 本地文件存储目录
```

### 3.3 中间件

| 中间件 | 功能 |
|--------|------|
| **CORSMiddleware** | 跨域请求处理，允许配置的 CORS 来源 |
| **请求计时** | 每个请求附加 `X-Process-Time` 响应头 |
| **慢请求告警** | 超过 1.5 秒的请求记录 WARNING 日志 |
| **启动迁移** | lifespan 中自动运行兼容迁移 + `Base.metadata.create_all` |

### 3.4 配置项 (核心)

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 连接串 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery 消息代理 |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery 结果存储 |
| `DB_POOL_SIZE` | 10 | 数据库连接池大小 |
| `DB_MAX_OVERFLOW` | 20 | 连接池溢出上限 |
| `DB_POOL_TIMEOUT` | 30s | 获取连接超时 |
| `DB_POOL_RECYCLE` | 1800s | 连接回收时间 |
| `STORAGE_BACKEND` | local | local / oss |
| `AI_GATEWAY_BASE_URL` | https://api.openai.com/v1 | AI Gateway |
| `AI_GATEWAY_MODEL` | gpt-4o-mini | 默认模型 |
| `SECRET_KEY` | change-me-in-production | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | - | Token 有效期 |

### 3.5 Windows 兼容处理

```python
# run_api.py & database.py
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.loops.asyncio.asyncio_loop_factory = lambda: asyncio.SelectorEventLoop
```

---

## 4. 前端架构

### 4.1 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Next.js (App Router) | 16.2.7 | 全栈 React 框架 |
| UI 库 | React | 19.2.4 | 组件渲染 |
| 语言 | TypeScript | ^5 | 类型安全 |
| 样式 | Tailwind CSS v4 | ^4 | 原子化 CSS |
| 组件库 | shadcn/ui (Radix UI) | - | UI 组件原语 |
| 图标 | lucide-react | ^1.17.0 | SVG 图标 |
| 构建 | Webpack (--webpack) | - | 打包 (非 Turbopack) |
| 字体 | Geist + Geist Mono | - | Vercel 字体 |

### 4.2 目录结构

```
lumio-frontend/
├── next.config.ts               # Next.js 配置
├── tsconfig.json                # TypeScript 配置
├── package.json                 # 依赖与脚本
├── postcss.config.mjs           # PostCSS (Tailwind v4)
├── components.json              # shadcn/ui 配置
├── public/                      # 静态资源
└── src/
    ├── app/                     # Next.js App Router 页面 (48个)
    │   ├── layout.tsx           # 根布局
    │   ├── page.tsx             # 首页
    │   ├── globals.css          # 全局样式
    │   ├── login/               # 登录
    │   ├── register/            # 注册
    │   ├── product/             # 产品
    │   ├── solutions/           # 解决方案
    │   ├── pricing/             # 价格
    │   ├── blog/                # 博客
    │   ├── help/                # 帮助中心
    │   ├── templates/           # 模板中心
    │   ├── tools/               # 工具中心
    │   ├── workspace/           # 工作台
    │   ├── ai/                  # AI 助手
    │   ├── drive/               # 云盘
    │   ├── docs/                # 在线文档
    │   ├── knowledge/           # 知识库
    │   ├── tasks/               # 任务中心
    │   ├── team/                # 团队
    │   ├── usage/               # 用量统计
    │   ├── billing/             # 账单与额度
    │   ├── settings/            # 账号设置
    │   ├── admin/               # 后台管理
    │   ├── enterprise/          # 企业版后台
    │   ├── share/               # 公开分享
    │   └── split/               # 表格拆分工具
    ├── components/
    │   ├── layout/              # 公共布局
    │   │   ├── site-chrome.tsx   # 页面外壳 (路由感知)
    │   │   ├── site-header.tsx   # 官网导航栏 + MegaMenu
    │   │   └── site-footer.tsx   # 官网页脚
    │   ├── workspace/           # 工作区布局
    │   │   ├── auth-gate.tsx     # 认证守卫
    │   │   └── workspace-shell.tsx  # 工作区外壳
    │   ├── admin/               # 后台管理组件
    │   │   └── admin-list-page.tsx
    │   └── ui/                  # shadcn/ui 基础组件
    │       ├── button.tsx       # 按钮 (4变体/3尺寸)
    │       ├── card.tsx         # 卡片
    │       ├── input.tsx        # 输入框
    │       ├── badge.tsx        # 徽章
    │       └── app-modal.tsx    # 模态框
    └── lib/
        ├── api.ts               # API 调用层 (200+ 接口)
        ├── auth.ts              # 认证工具 (localStorage读写)
        └── utils.ts             # cn() 类名合并工具
```

### 4.3 状态管理

**无第三方状态管理库**，完全基于：

| 方式 | 用途 |
|------|------|
| `localStorage` | Token、用户信息、工作空间信息持久化 |
| `React useState` | 组件级局部状态 |
| `CustomEvent ("lumio-auth-changed")` | 跨组件认证状态同步 |
| `sessionStorage` | 认证校验缓存 |
| 模块级变量 (`cachedAuth`) | 避免重复读取 localStorage |
| URL 查询参数 | 页面间传参 |

### 4.4 布局策略

```
根布局 (layout.tsx)
  └── SiteChrome (路由感知布局切换器)
        │
        ├── 公开页面 (非 /workspace 前缀)
        │     ├── SiteHeader (导航栏 + MegaMenu + 搜索 + 登录)
        │     ├── <main>{children}</main>
        │     └── SiteFooter
        │
        └── 工作区页面 (/workspace, /ai, /drive, /docs, ...)
              └── AuthGate (认证守卫)
                    └── WorkspaceShell
                          ├── 左侧可折叠侧边栏 (11项导航)
                          ├── 顶部搜索栏
                          ├── <main>{children}</main>
                          ├── 右侧浮动工具面板 (帮助/反馈/偏好)
                          └── 账户面板
```

---

## 5. 数据模型

### 5.1 ORM 模型清单（22 个模型，8 个模块）

#### 用户模块 (user)
| 模型 | 表名 | 说明 |
|------|------|------|
| `User` | users | 用户基本信息 (姓名/手机/头像/语言/时区) |
| `AuthAccount` | auth_accounts | 认证账号 (邮箱/密码哈希/状态) |
| `UserSession` | user_sessions | 用户会话记录 |

#### 文件模块 (file)
| 模型 | 表名 | 说明 |
|------|------|------|
| `UploadedFile` | uploaded_files | 上传文件元信息 |

#### 云盘模块 (drive)
| 模型 | 表名 | 说明 |
|------|------|------|
| `WorkspaceFile` | workspace_files | 工作空间文件 |
| `Folder` | folders | 文件夹 |
| `FileVersion` | file_versions | 文件版本历史 |
| `FileShare` | file_shares | 文件分享链接 |

#### 文档模块 (document)
| 模型 | 表名 | 说明 |
|------|------|------|
| `Document` | documents | 在线文档 |
| `DocumentVersion` | document_versions | 文档版本历史 |
| `DocumentShare` | document_shares | 文档分享链接 |

#### 知识库模块 (knowledge)
| 模型 | 表名 | 说明 |
|------|------|------|
| `KnowledgeBase` | knowledge_bases | 知识库 |
| `KnowledgeSource` | knowledge_sources | 知识库来源 (文件/文档/手动) |
| `FileChunk` | file_chunks | 文件切片 |
| `FileEmbedding` | file_embeddings | 切片 Embedding 向量 |

#### AI 模块 (ai)
| 模型 | 表名 | 说明 |
|------|------|------|
| `AIConversation` | ai_conversations | AI 对话会话 |
| `AIMessage` | ai_messages | AI 对话消息 |
| `AIModelConfig` | ai_model_configs | AI 模型配置 |

#### 工作空间模块 (workspace)
| 模型 | 表名 | 说明 |
|------|------|------|
| `Workspace` | workspaces | 工作空间 |
| `WorkspaceMember` | workspace_members | 工作空间成员 |
| `Department` | departments | 部门 |
| `Role` | roles | 角色 |
| `RolePermission` | role_permissions | 角色权限 |
| `Permission` | permissions | 权限定义 |

#### 计费模块 (billing)
| 模型 | 表名 | 说明 |
|------|------|------|
| `Plan` | plans | 套餐/计划 |
| `Subscription` | subscriptions | 订阅 |
| `Order` | orders | 订单 |
| `Payment` | payments | 支付记录 |
| `PaymentProviderConfig` | payment_provider_configs | 支付渠道配置 |

#### 运营模块 (operations)
| 模型 | 表名 | 说明 |
|------|------|------|
| `Job` | jobs | 异步任务/作业 |
| `AuditLog` | audit_logs | 审计日志 |
| `UsageRecord` | usage_records | 用量记录 |

#### 任务模块 (task)
| 模型 | 表名 | 说明 |
|------|------|------|
| `ProcessingTask` | processing_tasks | 文件处理任务 |

#### 模板模块 (template)
| 模型 | 表名 | 说明 |
|------|------|------|
| `UserTemplate` | user_templates | 用户模板 |

---

## 6. API 接口设计

### 6.1 全局配置

- **前缀**: `/api/v1`
- **认证**: Bearer Token (JWT HS256)
- **超时**: 30 秒
- **慢请求告警**: 1.5 秒

### 6.2 路由模块（21 个）

| # | 路由 | 前缀 | 功能 |
|---|------|------|------|
| 1 | health | / | 健康检查 GET |
| 2 | auth | /auth | 注册/登录/登出/个人信息/密码/注销 (7 端点) |
| 3 | users | /users | 用户信息查询/更新 (3 端点) |
| 4 | files | /files | 文件上传/列解析 (2 端点) |
| 5 | folders | /folders | 文件夹 CRUD (3 端点) |
| 6 | documents | /documents | 在线文档 CRUD/AI写作/导出/分享 |
| 7 | drive | /drive | 云盘文件管理/版本/分享 |
| 8 | file-ai | /file-ai | 文件索引/问答/总结/表格处理 |
| 9 | knowledge-bases | /knowledge-bases | 知识库 CRUD/来源/同步/问答 |
| 10 | ai | /ai | AI 对话管理 |
| 11 | chat | /chat | 聊天/流式聊天 |
| 12 | tasks | /tasks | Excel 拆分任务 CRUD/预览 |
| 13 | templates | /templates | 模板中心 CRUD |
| 14 | workspaces | /workspaces | 工作空间管理 |
| 15 | team | /team | 成员/部门/角色/权限/审计 |
| 16 | billing | /billing | 套餐/订单/支付/订阅 |
| 17 | usage | /usage | 用量统计查询 |
| 18 | admin | /admin | 后台管理全模块 |
| 19 | integrations | /integrations | 外部服务集成状态 |
| 20 | jobs | /jobs | 异步任务状态 |
| 21 | share | /share | 公开分享访问 |

---

## 7. 部署架构

### 7.1 Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]

  # PostgreSQL 使用本地安装的 Windows 服务
  # 数据库: lumio | 用户: postgres
```

### 7.2 启动流程

```
1. 启动 PostgreSQL (本地 Windows 服务)
2. docker compose up -d redis
3. cd backend && python run_api.py        → localhost:8000
4. cd lumio-frontend && npx next dev      → localhost:3000
```

### 7.3 环境变量 (.env)

```
DATABASE_URL=postgresql+asyncpg://postgres:{PASSWORD}@localhost:5432/lumio
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
STORAGE_BACKEND=local
AI_GATEWAY_BASE_URL=https://api.openai.com/v1
AI_GATEWAY_API_KEY=
AI_GATEWAY_MODEL=gpt-4o-mini
SECRET_KEY=change-me-in-production
```

---

## 8. 安全设计

| 层面 | 措施 |
|------|------|
| 传输安全 | Bearer Token (JWT HS256) |
| 密码存储 | PBKDF2-SHA256 (260,000 次迭代) |
| 跨域防护 | FastAPI CORSMiddleware (白名单配置) |
| 认证守卫 | 前端 AuthGate 组件 (未登录重定向) |
| 空间隔离 | 工作空间级数据隔离 |
| 权限控制 | 角色-权限模型 (RBAC) |
| 审计追踪 | AuditLog 全操作记录 |
| 输入验证 | Pydantic Schema 校验 |

---

## 9. 前端页面清单

### 9.1 官网公共页面 (17 个)

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 首页 | Hero + 6大能力 + 6大方案 + 数据亮点 + CTA |
| `/product` | 产品总览 | 8个产品卡片 |
| `/product/[slug]` | 产品详情 | 能力要点 + 操作入口 |
| `/solutions` | 解决方案 | 8个行业方案 |
| `/solutions/[slug]` | 方案详情 | 工作流程 + 关键指标 |
| `/pricing` | 价格 | 4套餐 + 功能对比表 |
| `/login` | 登录 | 账号密码登录 |
| `/register` | 注册 | 4步入门引导 |
| `/help` | 资源中心 | 7个资源入口 |
| `/help/[slug]` | 帮助详情 | 教程/案例/API/安全 |
| `/blog` | 博客列表 | 产品与技术实践 |
| `/blog/[slug]` | 博客详情 | 文章内容 |
| `/templates` | 模板中心 | 6个可复用模板 |
| `/tools` | 工具中心 | 拆分/AI/模板 |
| `/split` | 表格拆分 | 按列值/行数/工作表拆分 |
| `/share/documents/[token]` | 分享文档 | 公开文档查看 |
| `/share/files/[token]` | 分享文件 | 公开文件查看+下载 |

### 9.2 工作台页面 (31 个)

| 路由 | 页面 | 功能 |
|------|------|------|
| `/workspace` | 工作台首页 | 仪表盘: 快捷操作/最近文件/AI会话 |
| `/ai` | AI 助手 | 多轮对话, 上下文来自文件/知识库 |
| `/drive` | 云盘 | 文件 CRUD/AI处理/分享 |
| `/drive/folders/[id]` | 文件夹 | 文件夹内容浏览 |
| `/drive/files/[id]` | 文件预览 | 预览+AI处理 |
| `/drive/files/[id]/ai` | 文件AI | 索引/摘要/问答+引用 |
| `/docs` | 在线文档 | 编辑器/AI写作/导出 |
| `/knowledge` | 知识库 | 创建/来源/问答/权限 |
| `/knowledge/[id]/...` | 知识库子页 | 详情/成员/设置/来源 |
| `/tasks` | 任务中心 | 任务列表+进度追踪 |
| `/team` | 团队 | 成员/部门/角色/审计 |
| `/team/departments` | 部门 | 部门管理 |
| `/team/roles` | 角色权限 | 角色+权限分配 |
| `/team/members/[id]` | 成员详情 | 编辑角色/部门 |
| `/usage` | 用量统计 | 存储/AI/文件用量 |
| `/billing` | 账单与额度 | 套餐/支付/订单 |
| `/billing/checkout/[no]` | 支付结算 | 订单支付 |
| `/settings` | 账号设置 | 6Tab（资料/安全/绑定/通知/数据/注销） |
| `/workspace/settings` | 工作空间设置 | 名称/语言/时区 |
| `/admin` | 后台管理 | 总览仪表盘 |
| `/admin/users` | 用户管理 | 成员列表 |
| `/admin/workspaces` | 空间管理 | 空间+套餐 |
| `/admin/audit` | 审计日志 | 操作记录 |
| `/admin/models` | 模型配置 | AI/Embedding模型 |
| `/admin/orders` | 订单管理 | 订单列表 |
| `/admin/payments` | 支付记录 | 流水查询 |
| `/admin/storage` | 存储配置 | 存储状态 |
| `/admin/system` | 系统配置 | 环境/版本/开关 |
| `/enterprise` | 企业版后台 | 工作区/订阅/收入 |

**总计：48 个页面**

---

## 附录 A：代码仓库

| 项目 | 地址 |
|------|------|
| 后端 | https://github.com/xgxs525/lumio |
| 前端 | https://github.com/xgxs525/lumio-frontend |
