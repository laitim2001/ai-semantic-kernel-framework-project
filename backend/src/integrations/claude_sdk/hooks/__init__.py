"""Claude SDK Hooks System.

Sprint 49: S49-3 - Hooks System (10 pts)
Provides hook infrastructure for intercepting and controlling
Claude SDK operations.

Hooks:
- ApprovalHook: Requires human confirmation for write operations
- AuditHook: Logs all activities with sensitive data redaction
- RateLimitHook: Limits tool execution rate and concurrent operations
- SandboxHook: Restricts file access to allowed paths

Example:
    from claude_sdk.hooks import Hook, HookChain, ApprovalHook, AuditHook

    # Create hook chain
    chain = HookChain()

    # Add approval hook for write operations
    async def request_approval(ctx):
        return await ask_user(f"Allow {ctx.tool_name}?")

    chain.add(ApprovalHook(approval_callback=request_approval))

    # Add audit logging
    chain.add(AuditHook(logger=my_logger))

    # Execute with hooks
    result = await chain.run_tool_call(context)
    if result.is_allowed:
        # Execute tool
        pass
"""

from .base import Hook, HookChain
from .approval import ApprovalHook, DEFAULT_APPROVAL_TOOLS, WRITE_OPERATIONS
from .audit import AuditHook, AuditEntry, AuditLog
from .rate_limit import RateLimitHook, RateLimitConfig, RateLimitStats
from .sandbox import SandboxHook, StrictSandboxHook, FILE_ACCESS_TOOLS

__all__ = [
    # Base classes
    "Hook",
    "HookChain",
    # Approval hook
    "ApprovalHook",
    "DEFAULT_APPROVAL_TOOLS",
    "WRITE_OPERATIONS",
    # Audit hook
    "AuditHook",
    "AuditEntry",
    "AuditLog",
    # Rate limit hook
    "RateLimitHook",
    "RateLimitConfig",
    "RateLimitStats",
    # Sandbox hook
    "SandboxHook",
    "StrictSandboxHook",
    "FILE_ACCESS_TOOLS",
]
