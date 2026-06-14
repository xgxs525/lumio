"""file ai and knowledge source metadata

Revision ID: 20260613_0002
Revises: 20260613_0001
Create Date: 2026-06-13 12:00:00
"""

from alembic import op

revision = "20260613_0002"
down_revision = "20260613_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS knowledge_base_id uuid")
    op.execute("ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS source_type varchar(40) NOT NULL DEFAULT 'file'")
    op.execute("ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS source_id uuid")
    op.execute("ALTER TABLE file_chunks ADD COLUMN IF NOT EXISTS title varchar(255)")
    op.execute("ALTER TABLE file_embeddings ADD COLUMN IF NOT EXISTS knowledge_base_id uuid")
    op.execute("ALTER TABLE file_embeddings ADD COLUMN IF NOT EXISTS source_type varchar(40) NOT NULL DEFAULT 'file'")
    op.execute("ALTER TABLE file_embeddings ADD COLUMN IF NOT EXISTS source_id uuid")
    op.execute("ALTER TABLE file_embeddings ALTER COLUMN file_id DROP NOT NULL")
    op.execute("ALTER TABLE file_embeddings ALTER COLUMN chunk_id DROP NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_file_chunks_knowledge_base_id ON file_chunks(knowledge_base_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_file_chunks_source ON file_chunks(source_type, source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_file_embeddings_knowledge_base_id ON file_embeddings(knowledge_base_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_file_embeddings_source ON file_embeddings(source_type, source_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_file_embeddings_source")
    op.execute("DROP INDEX IF EXISTS ix_file_embeddings_knowledge_base_id")
    op.execute("DROP INDEX IF EXISTS ix_file_chunks_source")
    op.execute("DROP INDEX IF EXISTS ix_file_chunks_knowledge_base_id")
    op.execute("ALTER TABLE file_embeddings DROP COLUMN IF EXISTS source_id")
    op.execute("ALTER TABLE file_embeddings DROP COLUMN IF EXISTS source_type")
    op.execute("ALTER TABLE file_embeddings DROP COLUMN IF EXISTS knowledge_base_id")
    op.execute("ALTER TABLE file_chunks DROP COLUMN IF EXISTS title")
    op.execute("ALTER TABLE file_chunks DROP COLUMN IF EXISTS source_id")
    op.execute("ALTER TABLE file_chunks DROP COLUMN IF EXISTS source_type")
    op.execute("ALTER TABLE file_chunks DROP COLUMN IF EXISTS knowledge_base_id")
    op.execute("ALTER TABLE knowledge_sources DROP COLUMN IF EXISTS metadata")
