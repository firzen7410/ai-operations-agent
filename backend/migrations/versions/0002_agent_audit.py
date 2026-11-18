"""Create agent run and tool execution tables."""

import sqlalchemy as sa
from alembic import op

revision = "0002_agent_audit"
down_revision = "0001_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed')", name="ck_agent_runs_status"),
    )
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("arguments", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("result", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('success', 'failed')", name="ck_tool_executions_status"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tool_executions_run_id", "tool_executions", ["run_id"])


def downgrade() -> None:
    op.drop_table("tool_executions")
    op.drop_table("agent_runs")
