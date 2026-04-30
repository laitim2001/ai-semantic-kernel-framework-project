"""Category 2: Tool Layer — production registry + executor + sandbox + 6 built-in tools.

Sprint 51.1 (Day 5): InMemoryToolRegistry / InMemoryToolExecutor /
make_echo_executor have been removed (CARRY-017 closeout). All consumers
should use ToolRegistryImpl + ToolExecutorImpl directly, or call
register_builtin_tools() / business_domain.make_default_executor().
"""

from collections.abc import Awaitable, Callable
from typing import Any

from agent_harness._contracts import ToolCall

from agent_harness.tools._abc import ToolExecutor, ToolRegistry
from agent_harness.tools.echo_tool import ECHO_TOOL_SPEC, echo_handler, make_echo_executor
from agent_harness.tools.exec_tools import (
    PYTHON_SANDBOX_SPEC,
    make_python_sandbox_handler,
)
from agent_harness.tools.executor import ToolExecutorImpl
from agent_harness.tools.hitl_tools import (
    REQUEST_APPROVAL_SPEC,
    request_approval_handler,
)
from agent_harness.tools.memory_tools import (
    MEMORY_SEARCH_SPEC,
    MEMORY_TOOL_SPECS,
    MEMORY_WRITE_SPEC,
    memory_placeholder_handler,
)
from agent_harness.tools.permissions import PermissionChecker, PermissionDecision
from agent_harness.tools.registry import ToolRegistryImpl
from agent_harness.tools.sandbox import (
    SandboxBackend,
    SandboxResult,
    SubprocessSandbox,
)
from agent_harness.tools.search_tools import (
    WEB_SEARCH_SPEC,
    WebSearchConfigError,
    make_web_search_handler,
)

ToolHandler = Callable[[ToolCall], Awaitable[str | dict[str, Any]]]


def register_builtin_tools(
    registry: ToolRegistry,
    handlers: dict[str, ToolHandler],
    *,
    sandbox_backend: SandboxBackend | None = None,
) -> None:
    """Register 6 built-in ToolSpecs + handlers (echo + python_sandbox + web_search +
    request_approval + memory_search/write placeholders).

    `handlers` is mutated in place — caller passes a (possibly pre-populated)
    handlers dict that will receive the new entries. Duplicate registration
    raises via ToolRegistryImpl.register; caller is responsible for ensuring
    a clean registry.
    """
    registry.register(ECHO_TOOL_SPEC)
    handlers["echo_tool"] = echo_handler

    registry.register(PYTHON_SANDBOX_SPEC)
    handlers["python_sandbox"] = make_python_sandbox_handler(sandbox_backend)

    registry.register(WEB_SEARCH_SPEC)
    handlers["web_search"] = make_web_search_handler()

    registry.register(REQUEST_APPROVAL_SPEC)
    handlers["request_approval"] = request_approval_handler

    for spec in MEMORY_TOOL_SPECS:
        registry.register(spec)
        handlers[spec.name] = memory_placeholder_handler


__all__ = [
    "ECHO_TOOL_SPEC",
    "MEMORY_SEARCH_SPEC",
    "MEMORY_TOOL_SPECS",
    "MEMORY_WRITE_SPEC",
    "PYTHON_SANDBOX_SPEC",
    "PermissionChecker",
    "PermissionDecision",
    "REQUEST_APPROVAL_SPEC",
    "SandboxBackend",
    "SandboxResult",
    "SubprocessSandbox",
    "ToolExecutor",
    "ToolExecutorImpl",
    "ToolHandler",
    "ToolRegistry",
    "ToolRegistryImpl",
    "WEB_SEARCH_SPEC",
    "WebSearchConfigError",
    "echo_handler",
    "make_echo_executor",
    "make_python_sandbox_handler",
    "make_web_search_handler",
    "memory_placeholder_handler",
    "register_builtin_tools",
    "request_approval_handler",
]
