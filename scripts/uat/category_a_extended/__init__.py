"""
Category A: Extended IT Ticket Lifecycle Tests

擴展現有 IT Ticket 測試，完整驗證以下功能：
- #1  Multi-turn conversation sessions
- #14 HITL with escalation
- #17 Voting system
- #20 Decompose complex tasks
- #21 Plan step generation
- #35 Redis LLM caching
- #36 Cache invalidation
- #39 Checkpoint state persistence
- #49 Graceful shutdown

Usage:
    python -m scripts.uat.category_a_extended.it_ticket_extended_test
"""

from .it_ticket_extended_test import CategoryAExtendedTest, CategoryATestResults

__all__ = ["CategoryAExtendedTest", "CategoryATestResults"]
