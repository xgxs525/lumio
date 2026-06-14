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

KNOWLEDGE_COLUMN_MIGRATIONS = [
    "ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS knowledge_base_id uuid",
    "ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS source_type varchar(40) NOT NULL DEFAULT 'file'",
    "ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS source_id uuid",
    "ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS title varchar(255)",
    "ALTER TABLE file_embeddings ADD COLUMN IF NOT EXISTS knowledge_base_id uuid",
    "ALTER TABLE file_embeddings ADD COLUMN IF NOT EXISTS source_type varchar(40) NOT NULL DEFAULT 'file'",
    "ALTER TABLE file_embeddings ADD COLUMN IF NOT EXISTS source_id uuid",
    "ALTER TABLE file_embeddings ALTER COLUMN file_id DROP NOT NULL",
    "ALTER TABLE file_embeddings ALTER COLUMN chunk_id DROP NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_file_chunks_knowledge_base_id ON file_chunks(knowledge_base_id)",
    "CREATE INDEX IF NOT EXISTS ix_file_chunks_source ON file_chunks(source_type, source_id)",
    "CREATE INDEX IF NOT EXISTS ix_file_embeddings_knowledge_base_id ON file_embeddings(knowledge_base_id)",
    "CREATE INDEX IF NOT EXISTS ix_file_embeddings_source ON file_embeddings(source_type, source_id)",
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

    if await _table_exists(conn, 'file_chunks') and await _table_exists(conn, 'file_embeddings'):
        for statement in KNOWLEDGE_COLUMN_MIGRATIONS:
            await conn.execute(text(statement))

    if await _table_exists(conn, 'plans') and await _table_exists(conn, 'subscriptions') and await _table_exists(conn, 'orders'):
        for statement in BILLING_COLUMN_MIGRATIONS:
            await conn.execute(text(statement))
