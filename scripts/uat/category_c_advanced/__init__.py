"""
Category C: Advanced Workflow Tests

獨立進階測試場景，驗證以下功能：
- #26 Sub-workflow composition
- #27 Recursive execution
- #34 External connector updates
- #37 Message prioritization

Usage:
    python -m scripts.uat.category_c_advanced.advanced_workflow_test
"""

from .advanced_workflow_test import CategoryCAdvancedTest, CategoryCTestResults

__all__ = ["CategoryCAdvancedTest", "CategoryCTestResults"]
