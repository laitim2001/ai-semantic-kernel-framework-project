"""infrastructure.db.migrations - Alembic migration package.

Sprint 49.2 establishes 4 migrations covering core ORM:
    0001_initial_identity:      tenants / users / roles / user_roles / role_permissions
    0002_sessions_partitioned:  sessions / messages (part.) / message_events (part.)
    0003_tools:                 tools_registry / tool_calls / tool_results
    0004_state:                 state_snapshots (append-only) / loop_states

Run from backend/:
    alembic upgrade head           # apply all migrations
    alembic downgrade base         # revert all migrations
    alembic current                # show current revision
    alembic history --verbose      # show full history

Per .claude/rules/sprint-workflow.md: each migration corresponds to one
checklist task; commit format ``feat(infrastructure-db, sprint-49-2): N.M ...``.
"""
