"""
File: backend/src/mock_services/__init__.py
Purpose: Mock backend FastAPI sub-service for V2 Phase 51-54 demo material.
Category: Mock services (test/demo infra; NOT production)
Scope: Phase 51 / Sprint 51.0
Owner: Sprint 51.0 plan §決策 1 (mock_services 位置選擇)

Description:
    Standalone FastAPI app on port 8001 that simulates 5 enterprise business
    domains (CRM / KB / Patrol / Correlation / Rootcause / Audit / Incident).
    Used by business_domain/<domain>/mock_executor.py via HTTP (httpx async).
    Phase 55 will replace this layer with real enterprise integrations
    (D365 / SAP / ServiceNow); deletion of this dir is intentional.

Created: 2026-04-30 (Sprint 51.0 Day 1)
Last Modified: 2026-04-30
"""
