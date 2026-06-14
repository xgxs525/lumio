"""commercial billing foundation

Revision ID: 20260614_0003
Revises: 20260613_0002
Create Date: 2026-06-14 10:00:00
"""

from alembic import op

revision = "20260614_0003"
down_revision = "20260613_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
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
        """
        CREATE TABLE IF NOT EXISTS payments (
            id uuid PRIMARY KEY,
            order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            provider varchar(80) NOT NULL DEFAULT 'mock_cn',
            provider_payment_id varchar(180),
            status varchar(40) NOT NULL DEFAULT 'pending',
            amount numeric(12, 2) NOT NULL DEFAULT 0,
            currency varchar(20) NOT NULL DEFAULT 'CNY',
            checkout_url text,
            paid_at timestamptz,
            raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS payment_provider_configs (
            id uuid PRIMARY KEY,
            code varchar(80) UNIQUE NOT NULL,
            name varchar(120) NOT NULL,
            provider_type varchar(40) NOT NULL DEFAULT 'mock',
            supported_currencies jsonb NOT NULL DEFAULT '[]'::jsonb,
            supported_regions jsonb NOT NULL DEFAULT '[]'::jsonb,
            active boolean NOT NULL DEFAULT true,
            sandbox boolean NOT NULL DEFAULT true,
            sort_order integer NOT NULL DEFAULT 0,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_plans_sort_order ON plans(sort_order)",
        "CREATE INDEX IF NOT EXISTS ix_subscriptions_current_period_end ON subscriptions(current_period_end)",
        "CREATE INDEX IF NOT EXISTS ix_orders_plan_id ON orders(plan_id)",
        "CREATE INDEX IF NOT EXISTS ix_orders_user_id ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_orders_provider_order_id ON orders(provider_order_id)",
        "CREATE INDEX IF NOT EXISTS ix_orders_expires_at ON orders(expires_at)",
        "CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id)",
        "CREATE INDEX IF NOT EXISTS ix_payments_provider ON payments(provider)",
        "CREATE INDEX IF NOT EXISTS ix_payments_provider_payment_id ON payments(provider_payment_id)",
        "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_provider_configs_code ON payment_provider_configs(code)",
        "CREATE INDEX IF NOT EXISTS ix_payment_provider_configs_active ON payment_provider_configs(active)",
    ]
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payment_provider_configs")
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("DROP INDEX IF EXISTS ix_orders_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_orders_provider_order_id")
    op.execute("DROP INDEX IF EXISTS ix_orders_user_id")
    op.execute("DROP INDEX IF EXISTS ix_orders_plan_id")
    op.execute("DROP INDEX IF EXISTS ix_subscriptions_current_period_end")
    op.execute("DROP INDEX IF EXISTS ix_plans_sort_order")
    for table, columns in {
        "orders": [
            "expires_at",
            "description",
            "region",
            "locale",
            "provider_order_id",
            "billing_cycle",
            "order_type",
            "user_id",
            "plan_id",
        ],
        "subscriptions": [
            "metadata",
            "current_period_end",
            "current_period_start",
            "cancel_at_period_end",
            "seats",
            "provider",
        ],
        "plans": [
            "locale_labels",
            "payment_options",
            "model_policy",
            "sort_order",
            "enterprise_support_enabled",
            "advanced_model_enabled",
            "member_limit",
            "ai_request_quota",
            "currency",
            "price_yearly",
        ],
    }.items():
        for column in columns:
            op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")
