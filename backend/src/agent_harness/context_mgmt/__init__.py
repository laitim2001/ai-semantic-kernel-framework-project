"""Category 4: Context Management (compaction + masking + token counting + caching).

Re-exports the 5 Cat 4 ABCs:
    - Compactor (compactor/_abc.py)
    - ObservationMasker, JITRetrieval (_abc.py)
    - TokenCounter (token_counter/_abc.py)
    - PromptCacheManager (cache_manager.py)

See README.md for category overview; 17.md §2.1 for canonical ABC list.
"""

from agent_harness.context_mgmt._abc import JITRetrieval, ObservationMasker
from agent_harness.context_mgmt.cache_manager import PromptCacheManager
from agent_harness.context_mgmt.compactor import Compactor
from agent_harness.context_mgmt.token_counter import TokenCounter

__all__ = [
    "Compactor",
    "ObservationMasker",
    "JITRetrieval",
    "TokenCounter",
    "PromptCacheManager",
]
