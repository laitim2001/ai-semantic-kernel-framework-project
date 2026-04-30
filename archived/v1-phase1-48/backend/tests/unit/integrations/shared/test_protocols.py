"""
Tests for shared Protocol definitions.

Sprint 116: Validates Protocol interfaces, data transfer objects,
and protocol compliance checking.

Test groups:
1. ToolCallEvent: creation, to_dict, defaults
2. ToolResultEvent: creation, to_dict, status handling
3. ExecutionRequest: creation, to_dict, defaults
4. ExecutionResult: creation, to_dict, success/error states
5. SwarmEvent: creation, to_dict
6. ToolCallbackProtocol: structural compliance, isinstance checks
7. ExecutionEngineProtocol: structural compliance, isinstance checks
8. OrchestrationCallbackProtocol: structural compliance
9. SwarmCallbackProtocol: structural compliance
10. check_protocol_compliance: compliant/non-compliant objects
11. ToolCallStatus enum: all values
"""

import pytest
from datetime import datetime
from typing import Any, Dict

from src.integrations.shared.protocols import (
    ToolCallbackProtocol,
    ToolCallEvent,
    ToolCallStatus,
    ToolResultEvent,
    ExecutionEngineProtocol,
    ExecutionRequest,
    ExecutionResult,
    OrchestrationCallbackProtocol,
    SwarmCallbackProtocol,
    SwarmEvent,
    check_protocol_compliance,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_timestamp() -> datetime:
    """Fixed timestamp for deterministic tests."""
    return datetime(2026, 2, 24, 12, 0, 0)


@pytest.fixture
def tool_call_event(sample_timestamp: datetime) -> ToolCallEvent:
    """Create a fully-populated ToolCallEvent."""
    return ToolCallEvent(
        tool_name="bash",
        tool_id="tc-001",
        input_params={"command": "ls -la"},
        is_mcp=True,
        timestamp=sample_timestamp,
        worker_id="worker-1",
        metadata={"source": "test"},
    )


@pytest.fixture
def tool_result_event(sample_timestamp: datetime) -> ToolResultEvent:
    """Create a fully-populated ToolResultEvent."""
    return ToolResultEvent(
        tool_name="bash",
        tool_id="tc-001",
        status=ToolCallStatus.COMPLETED,
        result={"output": "file1.txt file2.txt"},
        error=None,
        duration_ms=150.5,
        timestamp=sample_timestamp,
        worker_id="worker-1",
    )


@pytest.fixture
def execution_request() -> ExecutionRequest:
    """Create a fully-populated ExecutionRequest."""
    return ExecutionRequest(
        intent="Analyze server logs for errors",
        context={"session_history": ["previous command"]},
        tools=[{"name": "bash", "description": "Run commands"}],
        max_tokens=4096,
        timeout=30.0,
        session_id="session-abc",
        metadata={"priority": "high"},
    )


@pytest.fixture
def execution_result() -> ExecutionResult:
    """Create a fully-populated ExecutionResult."""
    return ExecutionResult(
        success=True,
        content="Found 3 error entries in /var/log/syslog",
        error=None,
        framework_used="claude_sdk",
        tool_calls=[{"tool": "bash", "result": "ok"}],
        tokens_used=512,
        duration_ms=2500.0,
        metadata={"model": "claude-3-opus"},
    )


@pytest.fixture
def swarm_event(sample_timestamp: datetime) -> SwarmEvent:
    """Create a fully-populated SwarmEvent."""
    return SwarmEvent(
        event_type="worker_started",
        swarm_id="swarm-001",
        worker_id="worker-1",
        data={"task": "log analysis"},
        timestamp=sample_timestamp,
    )


# ---------------------------------------------------------------------------
# ToolCallStatus Tests
# ---------------------------------------------------------------------------


class TestToolCallStatus:
    """Tests for ToolCallStatus enum."""

    def test_all_status_values_exist(self) -> None:
        """All expected status values are defined."""
        expected = {"pending", "running", "completed", "failed", "cancelled"}
        actual = {status.value for status in ToolCallStatus}
        assert actual == expected

    def test_string_value(self) -> None:
        """Each status .value returns a string."""
        for status in ToolCallStatus:
            assert isinstance(status.value, str)
            assert status.value == status.value.lower()

    def test_is_str_subclass(self) -> None:
        """ToolCallStatus is a str enum, so members are also strings."""
        assert isinstance(ToolCallStatus.PENDING, str)
        assert ToolCallStatus.COMPLETED == "completed"


# ---------------------------------------------------------------------------
# ToolCallEvent Tests
# ---------------------------------------------------------------------------


class TestToolCallEvent:
    """Tests for ToolCallEvent data transfer object."""

    def test_creation_minimal(self) -> None:
        """Create event with only required fields."""
        event = ToolCallEvent(tool_name="grep", tool_id="tc-100")

        assert event.tool_name == "grep"
        assert event.tool_id == "tc-100"
        assert event.input_params == {}
        assert event.is_mcp is False
        assert isinstance(event.timestamp, datetime)
        assert event.worker_id is None
        assert event.metadata == {}

    def test_creation_full(self, tool_call_event: ToolCallEvent) -> None:
        """Create event with all fields populated."""
        assert tool_call_event.tool_name == "bash"
        assert tool_call_event.tool_id == "tc-001"
        assert tool_call_event.input_params == {"command": "ls -la"}
        assert tool_call_event.is_mcp is True
        assert tool_call_event.worker_id == "worker-1"
        assert tool_call_event.metadata == {"source": "test"}

    def test_to_dict(
        self,
        tool_call_event: ToolCallEvent,
        sample_timestamp: datetime,
    ) -> None:
        """Serialization produces correct dictionary with ISO timestamp."""
        d = tool_call_event.to_dict()

        assert d["tool_name"] == "bash"
        assert d["tool_id"] == "tc-001"
        assert d["input_params"] == {"command": "ls -la"}
        assert d["is_mcp"] is True
        assert d["timestamp"] == sample_timestamp.isoformat()
        assert d["worker_id"] == "worker-1"
        assert d["metadata"] == {"source": "test"}

    def test_defaults_produce_independent_dicts(self) -> None:
        """Default mutable fields are independent between instances."""
        event_a = ToolCallEvent(tool_name="a", tool_id="1")
        event_b = ToolCallEvent(tool_name="b", tool_id="2")

        event_a.input_params["key"] = "value"
        assert "key" not in event_b.input_params

        event_a.metadata["extra"] = True
        assert "extra" not in event_b.metadata


# ---------------------------------------------------------------------------
# ToolResultEvent Tests
# ---------------------------------------------------------------------------


class TestToolResultEvent:
    """Tests for ToolResultEvent data transfer object."""

    def test_creation_success(self, tool_result_event: ToolResultEvent) -> None:
        """Create a successful result event."""
        assert tool_result_event.tool_name == "bash"
        assert tool_result_event.tool_id == "tc-001"
        assert tool_result_event.status == ToolCallStatus.COMPLETED
        assert tool_result_event.result == {"output": "file1.txt file2.txt"}
        assert tool_result_event.error is None
        assert tool_result_event.duration_ms == 150.5

    def test_creation_failure(self, sample_timestamp: datetime) -> None:
        """Create a failed result event with error message."""
        event = ToolResultEvent(
            tool_name="bash",
            tool_id="tc-002",
            status=ToolCallStatus.FAILED,
            result=None,
            error="Permission denied: /root/secret",
            duration_ms=10.0,
            timestamp=sample_timestamp,
        )

        assert event.status == ToolCallStatus.FAILED
        assert event.result is None
        assert event.error == "Permission denied: /root/secret"

    def test_to_dict(
        self,
        tool_result_event: ToolResultEvent,
        sample_timestamp: datetime,
    ) -> None:
        """Serialization includes status value string."""
        d = tool_result_event.to_dict()

        assert d["tool_name"] == "bash"
        assert d["tool_id"] == "tc-001"
        assert d["status"] == "completed"
        assert d["result"] == {"output": "file1.txt file2.txt"}
        assert d["error"] is None
        assert d["duration_ms"] == 150.5
        assert d["timestamp"] == sample_timestamp.isoformat()
        assert d["worker_id"] == "worker-1"

    def test_status_is_enum(self) -> None:
        """Default status field is a ToolCallStatus enum."""
        event = ToolResultEvent(tool_name="test", tool_id="t-1")
        assert isinstance(event.status, ToolCallStatus)
        assert event.status == ToolCallStatus.COMPLETED


# ---------------------------------------------------------------------------
# ExecutionRequest Tests
# ---------------------------------------------------------------------------


class TestExecutionRequest:
    """Tests for ExecutionRequest data transfer object."""

    def test_creation_minimal(self) -> None:
        """Create request with only the intent field."""
        request = ExecutionRequest(intent="Check disk usage")

        assert request.intent == "Check disk usage"
        assert request.context == {}
        assert request.tools is None
        assert request.max_tokens is None
        assert request.timeout is None
        assert request.session_id is None
        assert request.metadata == {}

    def test_creation_full(self, execution_request: ExecutionRequest) -> None:
        """Create request with all fields populated."""
        assert execution_request.intent == "Analyze server logs for errors"
        assert execution_request.context == {"session_history": ["previous command"]}
        assert execution_request.tools == [{"name": "bash", "description": "Run commands"}]
        assert execution_request.max_tokens == 4096
        assert execution_request.timeout == 30.0
        assert execution_request.session_id == "session-abc"
        assert execution_request.metadata == {"priority": "high"}

    def test_to_dict(self, execution_request: ExecutionRequest) -> None:
        """Serialization produces complete dictionary."""
        d = execution_request.to_dict()

        assert d["intent"] == "Analyze server logs for errors"
        assert d["context"] == {"session_history": ["previous command"]}
        assert d["tools"] == [{"name": "bash", "description": "Run commands"}]
        assert d["max_tokens"] == 4096
        assert d["timeout"] == 30.0
        assert d["session_id"] == "session-abc"
        assert d["metadata"] == {"priority": "high"}


# ---------------------------------------------------------------------------
# ExecutionResult Tests
# ---------------------------------------------------------------------------


class TestExecutionResult:
    """Tests for ExecutionResult data transfer object."""

    def test_success_result(self, execution_result: ExecutionResult) -> None:
        """Create a successful execution result."""
        assert execution_result.success is True
        assert execution_result.content == "Found 3 error entries in /var/log/syslog"
        assert execution_result.error is None
        assert execution_result.framework_used == "claude_sdk"
        assert execution_result.tool_calls == [{"tool": "bash", "result": "ok"}]
        assert execution_result.tokens_used == 512
        assert execution_result.duration_ms == 2500.0

    def test_error_result(self) -> None:
        """Create an error execution result."""
        result = ExecutionResult(
            success=False,
            content="",
            error="Timeout after 30s",
            framework_used="agent_framework",
        )

        assert result.success is False
        assert result.content == ""
        assert result.error == "Timeout after 30s"
        assert result.framework_used == "agent_framework"

    def test_to_dict(self, execution_result: ExecutionResult) -> None:
        """Serialization produces complete dictionary."""
        d = execution_result.to_dict()

        assert d["success"] is True
        assert d["content"] == "Found 3 error entries in /var/log/syslog"
        assert d["error"] is None
        assert d["framework_used"] == "claude_sdk"
        assert d["tool_calls"] == [{"tool": "bash", "result": "ok"}]
        assert d["tokens_used"] == 512
        assert d["duration_ms"] == 2500.0
        assert d["metadata"] == {"model": "claude-3-opus"}

    def test_defaults(self) -> None:
        """Default values for optional fields."""
        result = ExecutionResult(success=True)

        assert result.content == ""
        assert result.error is None
        assert result.framework_used == ""
        assert result.tool_calls == []
        assert result.tokens_used == 0
        assert result.duration_ms == 0.0
        assert result.metadata == {}


# ---------------------------------------------------------------------------
# SwarmEvent Tests
# ---------------------------------------------------------------------------


class TestSwarmEvent:
    """Tests for SwarmEvent data transfer object."""

    def test_creation(self, swarm_event: SwarmEvent) -> None:
        """Create a fully-populated swarm event."""
        assert swarm_event.event_type == "worker_started"
        assert swarm_event.swarm_id == "swarm-001"
        assert swarm_event.worker_id == "worker-1"
        assert swarm_event.data == {"task": "log analysis"}

    def test_to_dict(
        self,
        swarm_event: SwarmEvent,
        sample_timestamp: datetime,
    ) -> None:
        """Serialization produces correct dictionary."""
        d = swarm_event.to_dict()

        assert d["event_type"] == "worker_started"
        assert d["swarm_id"] == "swarm-001"
        assert d["worker_id"] == "worker-1"
        assert d["data"] == {"task": "log analysis"}
        assert d["timestamp"] == sample_timestamp.isoformat()

    def test_defaults(self) -> None:
        """Default values for optional fields."""
        event = SwarmEvent(event_type="init", swarm_id="s-1")

        assert event.worker_id is None
        assert event.data == {}
        assert isinstance(event.timestamp, datetime)


# ---------------------------------------------------------------------------
# ToolCallbackProtocol Tests
# ---------------------------------------------------------------------------


class TestToolCallbackProtocol:
    """Tests for ToolCallbackProtocol structural subtyping."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Protocol can be used with isinstance() at runtime."""
        assert hasattr(ToolCallbackProtocol, "__protocol_attrs__") or hasattr(
            ToolCallbackProtocol, "__abstractmethods__"
        ) or callable(getattr(ToolCallbackProtocol, "__instancecheck__", None))

    def test_compliant_class_isinstance(self) -> None:
        """A class with matching methods passes isinstance check."""

        class CompliantHandler:
            async def on_tool_call(self, event: ToolCallEvent) -> Dict[str, Any]:
                return {"approved": True}

            async def on_tool_result(self, event: ToolResultEvent) -> None:
                pass

        handler = CompliantHandler()
        assert isinstance(handler, ToolCallbackProtocol)

    def test_non_compliant_class_not_isinstance(self) -> None:
        """A class missing methods fails isinstance check."""

        class IncompleteHandler:
            async def on_tool_call(self, event: ToolCallEvent) -> Dict[str, Any]:
                return {}

            # Missing on_tool_result

        handler = IncompleteHandler()
        assert not isinstance(handler, ToolCallbackProtocol)

    def test_structural_subtyping_no_inheritance(self) -> None:
        """Compliance works without explicit Protocol inheritance."""

        class StandaloneHandler:
            async def on_tool_call(self, event: ToolCallEvent) -> Dict[str, Any]:
                return {"logged": True}

            async def on_tool_result(self, event: ToolResultEvent) -> None:
                return None

        handler = StandaloneHandler()
        # No inheritance from ToolCallbackProtocol, but structurally matches
        assert isinstance(handler, ToolCallbackProtocol)


# ---------------------------------------------------------------------------
# ExecutionEngineProtocol Tests
# ---------------------------------------------------------------------------


class TestExecutionEngineProtocol:
    """Tests for ExecutionEngineProtocol structural subtyping."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Protocol can be used with isinstance() at runtime."""
        assert hasattr(ExecutionEngineProtocol, "__protocol_attrs__") or hasattr(
            ExecutionEngineProtocol, "__abstractmethods__"
        ) or callable(getattr(ExecutionEngineProtocol, "__instancecheck__", None))

    def test_compliant_class_isinstance(self) -> None:
        """A class with matching methods passes isinstance check."""

        class MockEngine:
            async def execute(self, request: ExecutionRequest) -> ExecutionResult:
                return ExecutionResult(success=True, content="done")

            async def is_available(self) -> bool:
                return True

        engine = MockEngine()
        assert isinstance(engine, ExecutionEngineProtocol)

    def test_non_compliant_class_not_isinstance(self) -> None:
        """A class missing methods fails isinstance check."""

        class PartialEngine:
            async def execute(self, request: ExecutionRequest) -> ExecutionResult:
                return ExecutionResult(success=True)

            # Missing is_available

        engine = PartialEngine()
        assert not isinstance(engine, ExecutionEngineProtocol)

    def test_structural_subtyping_no_inheritance(self) -> None:
        """Compliance works without explicit Protocol inheritance."""

        class IndependentEngine:
            async def execute(self, request: ExecutionRequest) -> ExecutionResult:
                return ExecutionResult(success=False, error="not implemented")

            async def is_available(self) -> bool:
                return False

        engine = IndependentEngine()
        assert isinstance(engine, ExecutionEngineProtocol)


# ---------------------------------------------------------------------------
# OrchestrationCallbackProtocol Tests
# ---------------------------------------------------------------------------


class TestOrchestrationCallbackProtocol:
    """Tests for OrchestrationCallbackProtocol structural subtyping."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Protocol can be used with isinstance() at runtime."""
        assert hasattr(OrchestrationCallbackProtocol, "__protocol_attrs__") or hasattr(
            OrchestrationCallbackProtocol, "__abstractmethods__"
        ) or callable(
            getattr(OrchestrationCallbackProtocol, "__instancecheck__", None)
        )

    def test_compliant_class_isinstance(self) -> None:
        """A class with all three methods passes isinstance check."""

        class FullCallbackHandler:
            async def on_execution_started(
                self, request: ExecutionRequest
            ) -> None:
                pass

            async def on_execution_completed(
                self, result: ExecutionResult
            ) -> None:
                pass

            async def on_execution_error(
                self, request: ExecutionRequest, error: str
            ) -> None:
                pass

        handler = FullCallbackHandler()
        assert isinstance(handler, OrchestrationCallbackProtocol)

    def test_non_compliant_class_not_isinstance(self) -> None:
        """A class missing one method fails isinstance check."""

        class PartialCallbackHandler:
            async def on_execution_started(
                self, request: ExecutionRequest
            ) -> None:
                pass

            async def on_execution_completed(
                self, result: ExecutionResult
            ) -> None:
                pass

            # Missing on_execution_error

        handler = PartialCallbackHandler()
        assert not isinstance(handler, OrchestrationCallbackProtocol)


# ---------------------------------------------------------------------------
# SwarmCallbackProtocol Tests
# ---------------------------------------------------------------------------


class TestSwarmCallbackProtocol:
    """Tests for SwarmCallbackProtocol structural subtyping."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Protocol can be used with isinstance() at runtime."""
        assert hasattr(SwarmCallbackProtocol, "__protocol_attrs__") or hasattr(
            SwarmCallbackProtocol, "__abstractmethods__"
        ) or callable(getattr(SwarmCallbackProtocol, "__instancecheck__", None))

    def test_compliant_class_isinstance(self) -> None:
        """A class with on_swarm_event passes isinstance check."""

        class SwarmHandler:
            async def on_swarm_event(self, event: SwarmEvent) -> None:
                pass

        handler = SwarmHandler()
        assert isinstance(handler, SwarmCallbackProtocol)


# ---------------------------------------------------------------------------
# check_protocol_compliance Tests
# ---------------------------------------------------------------------------


class TestCheckProtocolCompliance:
    """Tests for the check_protocol_compliance utility function."""

    def test_compliant_object(self) -> None:
        """Fully compliant object returns compliant=True, empty missing_methods."""

        class GoodEngine:
            async def execute(self, request: ExecutionRequest) -> ExecutionResult:
                return ExecutionResult(success=True)

            async def is_available(self) -> bool:
                return True

        result = check_protocol_compliance(GoodEngine(), ExecutionEngineProtocol)

        assert result["compliant"] is True
        assert result["missing_methods"] == []
        assert result["protocol_name"] == "ExecutionEngineProtocol"
        assert "execute" in result["checked_methods"]
        assert "is_available" in result["checked_methods"]

    def test_non_compliant_object(self) -> None:
        """Object missing all methods returns compliant=False and lists missing."""

        class EmptyObject:
            pass

        result = check_protocol_compliance(EmptyObject(), ToolCallbackProtocol)

        assert result["compliant"] is False
        assert "on_tool_call" in result["missing_methods"]
        assert "on_tool_result" in result["missing_methods"]
        assert result["protocol_name"] == "ToolCallbackProtocol"

    def test_partially_compliant_object(self) -> None:
        """Object with some methods returns the specific missing ones."""

        class PartialEngine:
            async def execute(self, request: ExecutionRequest) -> ExecutionResult:
                return ExecutionResult(success=True)

            # Missing is_available

        result = check_protocol_compliance(PartialEngine(), ExecutionEngineProtocol)

        assert result["compliant"] is False
        assert "is_available" in result["missing_methods"]
        assert "execute" not in result["missing_methods"]

    def test_non_callable_attribute(self) -> None:
        """Attribute that exists but is not callable is flagged."""

        class BadEngine:
            execute = "not a method"
            is_available = 42

        result = check_protocol_compliance(BadEngine(), ExecutionEngineProtocol)

        assert result["compliant"] is False
        # Both should be flagged as non-callable
        flagged_names = [m.split(" ")[0] for m in result["missing_methods"]]
        assert "execute" in flagged_names
        assert "is_available" in flagged_names


# ---------------------------------------------------------------------------
# Import verification: __init__.py re-exports
# ---------------------------------------------------------------------------


class TestModuleImports:
    """Verify that shared/__init__.py re-exports all public symbols."""

    def test_import_from_shared_package(self) -> None:
        """All protocols and DTOs are importable from the shared package."""
        from src.integrations.shared import (
            ToolCallbackProtocol as TCP,
            ToolCallEvent as TCE,
            ToolCallStatus as TCS,
            ToolResultEvent as TRE,
            ExecutionEngineProtocol as EEP,
            ExecutionRequest as ER,
            ExecutionResult as ERs,
            OrchestrationCallbackProtocol as OCP,
            SwarmCallbackProtocol as SCP,
            SwarmEvent as SE,
            check_protocol_compliance as cpc,
        )

        assert TCP is ToolCallbackProtocol
        assert TCE is ToolCallEvent
        assert TCS is ToolCallStatus
        assert TRE is ToolResultEvent
        assert EEP is ExecutionEngineProtocol
        assert ER is ExecutionRequest
        assert ERs is ExecutionResult
        assert OCP is OrchestrationCallbackProtocol
        assert SCP is SwarmCallbackProtocol
        assert SE is SwarmEvent
        assert cpc is check_protocol_compliance
