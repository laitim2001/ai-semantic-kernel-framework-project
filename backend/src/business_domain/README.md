# business_domain — V2 Enterprise Business Domains

> ⚠️ **DO NOT IMPLEMENT IN SPRINT 49.x.** Phase 55 (Production) is when
> business domains land. Sprint 49.1 only creates the directory shell.

## 5 domains (per 08b-business-tools-spec.md)

| Domain | Tools | Phase 55 sprint |
|--------|-------|-----------------|
| patrol | 4-6 (patrol_run / patrol_check / patrol_report) | 55.1 |
| correlation | 4-5 (event_correlate / pattern_match / temporal_join) | 55.2 |
| rootcause | 4-5 (rca_analyze / dependency_traverse / hypothesis_test) | 55.3 |
| audit_domain | 4 (audit_query / audit_export / compliance_check) | 55.4 |
| incident | 5-6 (incident_create / incident_update / incident_resolve / etc) | 55.5 |

(Total ~24 business tools.)

## Critical rules

- **Each domain owns its own ToolSpecs**; never put business tools in `agent_harness/tools/`
- **Each domain registers via** `register_<domain>_tools(registry)` at startup
- **Multi-tenant strict** — every domain query must include tenant_id
- **No cross-domain imports** without explicit architecture review

## Sprint 49.1 deliverable

Just empty `__init__.py` per domain to prove the package structure
is importable. Real impl waits for Phase 55.
