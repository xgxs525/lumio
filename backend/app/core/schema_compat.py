from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


USER_COLUMN_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone varchar(32)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash varchar(255) NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS name varchar(100) NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url text",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS locale varchar(20) NOT NULL DEFAULT 'zh-CN'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone varchar(64) NOT NULL DEFAULT 'Asia/Shanghai'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS status varchar(30) NOT NULL DEFAULT 'active'",
    "UPDATE users SET password_hash = hashed_password WHERE password_hash = '' AND hashed_password IS NOT NULL",
    "UPDATE users SET name = nickname WHERE name = '' AND nickname IS NOT NULL AND nickname != ''",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_not_null ON users(phone) WHERE phone IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_users_status ON users(status)",
]

TEMPLATE_COLUMN_MIGRATIONS = [
    "ALTER TABLE user_templates ADD COLUMN IF NOT EXISTS user_id uuid",
    "CREATE INDEX IF NOT EXISTS ix_user_templates_user_id ON user_templates(user_id)",
]

# Old knowledge tables are replaced by kb_* tables (see app/models/knowledge.py)
KNOWLEDGE_COLUMN_MIGRATIONS = []

FOLDER_COLUMN_MIGRATIONS = [
    "ALTER TABLE folders ADD COLUMN IF NOT EXISTS is_team_shared boolean NOT NULL DEFAULT false",
    "ALTER TABLE folders ADD COLUMN IF NOT EXISTS shared_by uuid",
    "ALTER TABLE folders ADD COLUMN IF NOT EXISTS deleted_by uuid",
    "ALTER TABLE folders ADD COLUMN IF NOT EXISTS trash_expire_at timestamptz",
    "ALTER TABLE folders ADD COLUMN IF NOT EXISTS original_parent_id uuid",
    "ALTER TABLE folders ADD COLUMN IF NOT EXISTS original_path text",
]
DRIVE_COLUMN_MIGRATIONS = [
    "ALTER TABLE files ADD COLUMN IF NOT EXISTS deleted_at timestamptz",
    "CREATE INDEX IF NOT EXISTS ix_files_deleted_at ON files(deleted_at)",
    "ALTER TABLE files ADD COLUMN IF NOT EXISTS deleted_by uuid",
    "ALTER TABLE files ADD COLUMN IF NOT EXISTS trash_expire_at timestamptz",
    "ALTER TABLE files ADD COLUMN IF NOT EXISTS original_parent_id uuid",
    "ALTER TABLE files ADD COLUMN IF NOT EXISTS original_path text",
]

BILLING_COLUMN_MIGRATIONS = [
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS price_yearly numeric(12, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS currency varchar(20) NOT NULL DEFAULT 'CNY'",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS ai_request_quota bigint NOT NULL DEFAULT 0",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS member_limit integer NOT NULL DEFAULT 1",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS advanced_model_enabled boolean NOT NULL DEFAULT false",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS enterprise_support_enabled boolean NOT NULL DEFAULT false",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS sort_order integer NOT NULL DEFAULT 0",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS model_policy jsonb NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS payment_options jsonb NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE plans ADD COLUMN IF NOT EXISTS locale_labels jsonb NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS provider varchar(80) NOT NULL DEFAULT 'mock_cn'",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS seats integer NOT NULL DEFAULT 1",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancel_at_period_end boolean NOT NULL DEFAULT false",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS current_period_start timestamptz",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS current_period_end timestamptz",
    "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS plan_id uuid",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS user_id uuid",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_type varchar(40) NOT NULL DEFAULT 'subscription'",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS billing_cycle varchar(30) NOT NULL DEFAULT 'monthly'",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS provider_order_id varchar(180)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS locale varchar(20) NOT NULL DEFAULT 'zh-CN'",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS region varchar(40) NOT NULL DEFAULT 'CN'",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS description text",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS expires_at timestamptz",
    "CREATE INDEX IF NOT EXISTS ix_plans_sort_order ON plans(sort_order)",
    "CREATE INDEX IF NOT EXISTS ix_subscriptions_current_period_end ON subscriptions(current_period_end)",
    "CREATE INDEX IF NOT EXISTS ix_orders_plan_id ON orders(plan_id)",
    "CREATE INDEX IF NOT EXISTS ix_orders_user_id ON orders(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_orders_provider_order_id ON orders(provider_order_id)",
    "CREATE INDEX IF NOT EXISTS ix_orders_expires_at ON orders(expires_at)",
]


async def _table_exists(conn: AsyncConnection, table_name: str) -> bool:
    result = await conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def run_compat_migrations(conn: AsyncConnection) -> None:
    """Small development migration bridge until Alembic migrations are introduced."""
    if not await _table_exists(conn, 'users'):
        return

    for statement in USER_COLUMN_MIGRATIONS:
        await conn.execute(text(statement))

    if await _table_exists(conn, 'user_templates'):
        for statement in TEMPLATE_COLUMN_MIGRATIONS:
            await conn.execute(text(statement))

    # Drop old knowledge tables (replaced by kb_* tables)
    for old_table in ('file_embeddings', 'file_chunks', 'knowledge_sources', 'knowledge_bases'):
        if await _table_exists(conn, old_table):
            await conn.execute(text(f'DROP TABLE IF EXISTS {old_table} CASCADE'))

    if await _table_exists(conn, 'plans') and await _table_exists(conn, 'subscriptions') and await _table_exists(conn, 'orders'):
        for statement in BILLING_COLUMN_MIGRATIONS:
            await conn.execute(text(statement))

    if await _table_exists(conn, 'folders'):
        for statement in FOLDER_COLUMN_MIGRATIONS:
            await conn.execute(text(statement))

    if await _table_exists(conn, 'files'):
        for statement in DRIVE_COLUMN_MIGRATIONS:
            await conn.execute(text(statement))

    if await _table_exists(conn, 'users'):
        for statement in [
            "CREATE TABLE IF NOT EXISTS password_resets ("
            "  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
            "  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
            "  token varchar(255) NOT NULL UNIQUE,"
            "  code varchar(8),"
            "  used boolean NOT NULL DEFAULT false,"
            "  expires_at timestamptz NOT NULL,"
            "  created_at timestamptz NOT NULL DEFAULT now()"
            ")",
            "CREATE INDEX IF NOT EXISTS ix_password_resets_user_id ON password_resets(user_id)",
            "CREATE INDEX IF NOT EXISTS ix_password_resets_token ON password_resets(token)",
            "CREATE INDEX IF NOT EXISTS ix_password_resets_expires_at ON password_resets(expires_at)",
        ]:
            await conn.execute(text(statement))

    if await _table_exists(conn, 'ai_conversations'):
        for statement in [
            "ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS is_pinned boolean NOT NULL DEFAULT false",
            "ALTER TABLE ai_conversations ADD COLUMN IF NOT EXISTS pinned_at timestamptz",
            "CREATE INDEX IF NOT EXISTS ix_ai_conversations_is_pinned ON ai_conversations(is_pinned)",
        ]:
            await conn.execute(text(statement))
