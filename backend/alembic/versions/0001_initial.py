"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("google_id", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255)),
        sa.Column("avatar_url", sa.String(512)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("name_ru", sa.String(100), nullable=False),
    )

    op.create_table(
        "words",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("text", sa.String(255), nullable=False, unique=True),
        sa.Column("translation", sa.String(255), nullable=False),
        sa.Column("transcription", sa.String(255)),
        sa.Column("part_of_speech", sa.String(32)),
        sa.Column("examples", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("audio_url", sa.String(512)),
        sa.Column("cefr_level", sa.String(2)),
        sa.Column("topic_id", sa.Integer, sa.ForeignKey("topics.id")),
        sa.Column("source", sa.String(16), nullable=False, server_default="user_added"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_words_topic", "words", ["topic_id"])
    op.create_index("idx_words_level", "words", ["cefr_level"])

    op.create_table(
        "user_words",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("added_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "word_id"),
    )
    op.create_index("idx_user_words_user", "user_words", ["user_id"])

    op.create_table(
        "fsrs_states",
        sa.Column("user_word_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_words.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="new"),
        sa.Column("step", sa.SmallInteger),
        sa.Column("stability", sa.Float),
        sa.Column("difficulty", sa.Float),
        sa.Column("due_date", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_review", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("idx_fsrs_due", "fsrs_states", ["due_date"])

    op.create_table(
        "review_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_word_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_words.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(16), nullable=False),
        sa.Column("rating", sa.SmallInteger, nullable=False),
        sa.Column("elapsed_days", sa.Float),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_review_logs_user_word", "review_logs", ["user_word_id"])


def downgrade() -> None:
    op.drop_table("review_logs")
    op.drop_table("fsrs_states")
    op.drop_table("user_words")
    op.drop_table("words")
    op.drop_table("topics")
    op.drop_table("users")
