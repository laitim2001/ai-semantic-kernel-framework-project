# =============================================================================
# IPA Platform - Audit API Module
# =============================================================================
# Sprint 3: 集成 & 可靠性 - 審計日誌系統
# Sprint 80: S80-2 - 自主決策審計追蹤 (8 pts)
#
# REST API 端點：
#   - 審計日誌查詢和導出 (Sprint 3)
#   - 決策審計追蹤 (Sprint 80)
# =============================================================================

from src.api.v1.audit.routes import router
from src.api.v1.audit.decision_routes import router as decision_router

__all__ = ["router", "decision_router"]
