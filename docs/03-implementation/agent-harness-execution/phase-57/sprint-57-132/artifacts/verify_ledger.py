"""Sprint 57.132 drive-through ledger verifier.

Queries the `messages` Cat-3 ledger for a chat session and prints each row's
role / tool_calls / tool_call_id / content snippet. For 57.132 this proves the
RESUME-path persist: a paused-then-approved tool's round-trip ([assistant
tool_use, tool result]) is persisted to the ledger AT RESUME (before 57.132 the
ledger held only [user, final-answer] for a resumed turn). Run from backend/
with PYTHONPATH=src.
"""

import asyncio
import json
import sys
from uuid import UUID

from sqlalchemy import select, text

from infrastructure.db.engine import get_session_factory
from infrastructure.db.models.sessions import Message

SESSION_ID = UUID(sys.argv[1] if len(sys.argv) > 1 else "02fa6bfb-4061-4b3a-87aa-8e4ef7f90a76")
TENANT_ID = UUID("09eb1b62-9fd3-439a-8229-1c923cc667e9")  # acme-prod


async def main() -> None:
    factory = get_session_factory()
    async with factory() as db:
        # Satisfy RLS (no-op if the app role bypasses it).
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": str(TENANT_ID)}
        )
        stmt = (
            select(Message)
            .where(Message.session_id == SESSION_ID, Message.tenant_id == TENANT_ID)
            .order_by(Message.sequence_num)
        )
        rows = (await db.execute(stmt)).scalars().all()
        print(f"messages rows for session {SESSION_ID}: {len(rows)}")
        for r in rows:
            content = r.content
            role = content.get("role") if isinstance(content, dict) else r.role
            tool_calls = content.get("tool_calls") if isinstance(content, dict) else None
            tcid = content.get("tool_call_id") if isinstance(content, dict) else None
            c = content.get("content") if isinstance(content, dict) else content
            snippet = c[:140] if isinstance(c, str) else json.dumps(c)[:140]
            tc = f"YES({tool_calls[0]['name']})" if tool_calls else "-"
            print(
                f"  seq={r.sequence_num} turn={r.turn_num} role={role} "
                f"tool_calls={tc} tool_call_id={tcid or '-'} content={snippet!r}"
            )


asyncio.run(main())
