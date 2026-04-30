"""
Session Features Module

Provides advanced features for Session mode.

Components:
- TagService: Manage session tags
- StatisticsService: Session statistics with lazy calculation
- TemplateService: Session templates

Usage:
    from src.domain.sessions.features import TagService, StatisticsService

    # Tags
    tags = TagService(repository=repo)
    await tags.add_tag(session_id, "important")

    # Statistics
    stats = StatisticsService(repository=repo, cache=cache)
    result = await stats.get_statistics(session_id)
"""

from .tags import TagService, Tag
from .statistics import StatisticsService, SessionStatistics
from .templates import TemplateService, SessionTemplate

__all__ = [
    # Tags
    "TagService",
    "Tag",
    # Statistics
    "StatisticsService",
    "SessionStatistics",
    # Templates
    "TemplateService",
    "SessionTemplate",
]
