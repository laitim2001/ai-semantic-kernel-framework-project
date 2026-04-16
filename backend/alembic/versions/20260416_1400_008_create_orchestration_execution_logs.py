"""Create orchestration_execution_logs table.

Sprint 169 — Phase 47: Pipeline execution persistence.

Revision ID: 008_orchestration_execution_logs
Revises: 007_agent_experts
Create Date: 2026-04-16
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers
revision: str = "008_orchestration_execution_logs"
down_revision: Union[str, None] = "007_agent_experts"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "orchestration_execution_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # Identifiers
        sa.Column("request_id", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("session_id", sa.String(100), nullable=False, index=True),
        sa.Column("user_id", sa.String(100), nullable=False, index=True),
        # Input
        sa.Column("user_input", sa.Text(), nullable=False),
        # Pipeline step outputs (JSONB)
        sa.Column("routing_decision", JSONB(), nullable=True),
        sa.Column("risk_assessment", JSONB(), nullable=True),
        sa.Column("completeness_info", JSONB(), nullable=True),
        # Route selection
        sa.Column("selected_route", sa.String(50), nullable=True, index=True),
        sa.Column("route_reasoning", sa.Text(), nullable=True),
        # Execution details (JSONB)
        sa.Column("pipeline_steps", JSONB(), nullable=True),
        sa.Column("agent_events", JSONB(), nullable=True),
        sa.Column("final_response", sa.Text(), nullable=True),
        sa.Column("dispatch_result", JSONB(), nullable=True),
        # Status
        sa.Column("status", sa.String(50), nullable=False, server_default="completed", index=True),
        sa.Column("error", sa.Text(), nullable=True),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_ms", sa.Float(), nullable=True),
        sa.Column("fast_path_applied", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("orchestration_execution_logs")
