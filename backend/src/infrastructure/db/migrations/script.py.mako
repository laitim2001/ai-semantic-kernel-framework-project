"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

File: backend/src/infrastructure/db/migrations/versions/${up_revision}_<slug>.py
Purpose: ${message}
Category: Infrastructure / Migration (Phase 49 Foundation)
Scope: Sprint 49.x

Modification History:
    - ${create_date.strftime("%Y-%m-%d") if hasattr(create_date, "strftime") else create_date}: Initial creation
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Apply schema changes."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert schema changes."""
    ${downgrades if downgrades else "pass"}
