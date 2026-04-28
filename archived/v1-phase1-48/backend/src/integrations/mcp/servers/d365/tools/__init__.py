"""D365 MCP Server Tools.

Sprint 129: Story 129-2

Tool categories:
    - QueryTools: Entity querying and metadata discovery (list, get, query, metadata)
    - CrudTools: Entity record creation and update (create, update)
"""

from .query import QueryTools
from .crud import CrudTools

__all__ = [
    "QueryTools",
    "CrudTools",
]
