"""Category 2: Tool Layer (registry + executor). See README.md.

50.x bring-up: in-memory registry + executor + echo_tool exported here for
test-helper convenience. DEPRECATED-IN: 51.1 (Cat 2 production impl).
"""

from agent_harness.tools._abc import ToolExecutor, ToolRegistry
from agent_harness.tools._inmemory import (
    ECHO_TOOL_SPEC,
    InMemoryToolExecutor,
    InMemoryToolRegistry,
    ToolHandler,
    echo_handler,
    make_echo_executor,
)
from agent_harness.tools.exec_tools import (
    PYTHON_SANDBOX_SPEC,
    make_python_sandbox_handler,
)
from agent_harness.tools.executor import ToolExecutorImpl
from agent_harness.tools.permissions import PermissionChecker, PermissionDecision
from agent_harness.tools.registry import ToolRegistryImpl
from agent_harness.tools.sandbox import (
    SandboxBackend,
    SandboxResult,
    SubprocessSandbox,
)

__all__ = [
    "ECHO_TOOL_SPEC",
    "InMemoryToolExecutor",
    "InMemoryToolRegistry",
    "PYTHON_SANDBOX_SPEC",
    "PermissionChecker",
    "PermissionDecision",
    "SandboxBackend",
    "SandboxResult",
    "SubprocessSandbox",
    "ToolExecutor",
    "ToolExecutorImpl",
    "ToolHandler",
    "ToolRegistry",
    "ToolRegistryImpl",
    "echo_handler",
    "make_echo_executor",
    "make_python_sandbox_handler",
]
