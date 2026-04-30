# platform/identity

Multi-tenant identity + RBAC + RLS context propagation.

**Implementation Phase**: 49.2 (tenant_id + JWT), 49.3 (RLS + RBAC), 53.4 (Teams SSO if applicable)
**Critical rule**: Every business endpoint MUST inject tenant context via dependency. See `.claude/rules/multi-tenant-data.md`.

## Sprint roadmap
- 49.2: tenant_id column rule + Pydantic Settings JWT config
- 49.3: PostgreSQL RLS policies + per-request `SET app.tenant_id` + RBAC roles table
