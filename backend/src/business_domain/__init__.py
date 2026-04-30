"""
business_domain — V2 enterprise business domains.

INTENTIONALLY EMPTY at Sprint 49.1. Phase 55 implements all 5 domains.

Per 08b-business-tools-spec.md: each domain owns its own ToolSpecs and
registers them via `register_<domain>_tools(registry)` helper at startup.

Domains:
- patrol      — operational patrol / monitoring
- correlation — event correlation analysis
- rootcause   — root cause analysis
- audit_domain — business audit + compliance
- incident    — incident management lifecycle
"""
