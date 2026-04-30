"""
core.exceptions — Common exception types.

Sprint 49.1: only IPABaseException. Each category will derive its own
domain exceptions (e.g. agent_harness.tools may define ToolError) but
they all chain to IPABaseException.
"""

from __future__ import annotations


class IPABaseException(Exception):
    """Base for all IPA Platform V2 exceptions.

    Categories should subclass this; never raise plain `Exception`.
    Per ABC rules, recovery decisions go through Cat 8 ErrorPolicy.
    """


__all__ = ["IPABaseException"]
