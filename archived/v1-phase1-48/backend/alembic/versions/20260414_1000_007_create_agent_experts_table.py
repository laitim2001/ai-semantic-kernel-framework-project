"""Create agent_experts table.

Sprint 163 — Phase 46 Agent Expert Registry.

Revision ID: 007_agent_experts
Revises: 006_sync_execution_model
Create Date: 2026-04-14
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers
revision: str = "007_agent_experts"
down_revision: Union[str, None] = "006_sync_execution_model"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "agent_experts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("display_name_zh", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("capabilities", JSONB(), nullable=False, server_default="[]"),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("tools", JSONB(), nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true", index=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("agent_experts")
