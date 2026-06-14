"""pgvector and first-phase API persistence baseline

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13 00:00:00
"""

from alembic import op

revision = "20260613_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION
            WHEN undefined_file OR feature_not_supported THEN
                RAISE NOTICE 'pgvector extension is not installed on this PostgreSQL server; keeping JSONB embeddings.';
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                ALTER TABLE file_embeddings
                    ADD COLUMN IF NOT EXISTS embedding_vector vector(1536);
                CREATE INDEX IF NOT EXISTS ix_file_embeddings_embedding_vector
                    ON file_embeddings USING ivfflat (embedding_vector vector_cosine_ops)
                    WITH (lists = 100);
            END IF;
        END $$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_records_workspace_created ON usage_records (workspace_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ai_conversations_workspace_updated ON ai_conversations (workspace_id, updated_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ai_conversations_workspace_updated")
    op.execute("DROP INDEX IF EXISTS ix_usage_records_workspace_created")
    op.execute("DROP INDEX IF EXISTS ix_file_embeddings_embedding_vector")
    op.execute("ALTER TABLE file_embeddings DROP COLUMN IF EXISTS embedding_vector")
