"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scraping_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", "paused", name="jobstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "engine",
            sa.Enum("playwright", "selenium", "httpx", name="scraperengine"),
            nullable=False,
            server_default="playwright",
        ),
        sa.Column("css_selector", sa.Text(), nullable=True),
        sa.Column("xpath_selector", sa.Text(), nullable=True),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delay_seconds", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scraping_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("scraping_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True, index=True),
        sa.Column("engine_used", sa.String(50), nullable=False),
        sa.Column("pages_scraped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_duplicated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(2048), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "scraped_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("scraping_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("scraping_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("raw", "validated", "duplicate", "rejected", name="itemstatus"),
            nullable=False,
            server_default="raw",
        ),
        sa.Column("content_hash", sa.String(64), nullable=True, index=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "proxy_pool",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column(
            "protocol",
            sa.Enum("http", "https", "socks5", name="proxyprotocol"),
            nullable=False,
            server_default="http",
        ),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("response_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("scraped_items")
    op.drop_table("scraping_sessions")
    op.drop_table("scraping_jobs")
    op.drop_table("proxy_pool")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS scraperengine")
    op.execute("DROP TYPE IF EXISTS itemstatus")
    op.execute("DROP TYPE IF EXISTS proxyprotocol")
