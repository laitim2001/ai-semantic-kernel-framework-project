"""
Category B: Concurrent Batch Processing Tests

批次並行處理場景，驗證以下功能：
- #15 Concurrent execution
- #22 Parallel branch management
- #23 Fan-out/Fan-in pattern
- #24 Branch timeout handling
- #25 Error isolation in branches
- #28 Nested workflow context

Usage:
    python -m scripts.uat.category_b_concurrent.concurrent_batch_test
"""

from .concurrent_batch_test import CategoryBConcurrentTest, CategoryBTestResults

__all__ = ["CategoryBConcurrentTest", "CategoryBTestResults"]
