"""
Unit tests for Swarm data models.

Tests serialization, deserialization, and model behavior.
"""

import json
from datetime import datetime

import pytest

from src.integrations.swarm.models import (
    AgentSwarmStatus,
    SwarmMode,
    SwarmStatus,
    ThinkingContent,
    ToolCallInfo,
    ToolCallStatus,
    WorkerExecution,
    WorkerMessage,
    WorkerStatus,
    WorkerType,
)


class TestEnums:
    """Test enum definitions."""

    def test_worker_type_values(self):
        """Test WorkerType enum values."""
        assert WorkerType.RESEARCH.value == "research"
        assert WorkerType.WRITER.value == "writer"
        assert WorkerType.DESIGNER.value == "designer"
        assert WorkerType.REVIEWER.value == "reviewer"
        assert WorkerType.COORDINATOR.value == "coordinator"
        assert WorkerType.CUSTOM.value == "custom"

    def test_worker_status_values(self):
        """Test WorkerStatus enum values."""
        assert WorkerStatus.PENDING.value == "pending"
        assert WorkerStatus.RUNNING.value == "running"
        assert WorkerStatus.THINKING.value == "thinking"
        assert WorkerStatus.TOOL_CALLING.value == "tool_calling"
        assert WorkerStatus.COMPLETED.value == "completed"
        assert WorkerStatus.FAILED.value == "failed"
        assert WorkerStatus.CANCELLED.value == "cancelled"

    def test_swarm_mode_values(self):
        """Test SwarmMode enum values."""
        assert SwarmMode.SEQUENTIAL.value == "sequential"
        assert SwarmMode.PARALLEL.value == "parallel"
        assert SwarmMode.HIERARCHICAL.value == "hierarchical"

    def test_swarm_status_values(self):
        """Test SwarmStatus enum values."""
        assert SwarmStatus.INITIALIZING.value == "initializing"
        assert SwarmStatus.RUNNING.value == "running"
        assert SwarmStatus.PAUSED.value == "paused"
        assert SwarmStatus.COMPLETED.value == "completed"
        assert SwarmStatus.FAILED.value == "failed"


class TestToolCallInfo:
    """Test ToolCallInfo dataclass."""

    def test_create_tool_call(self):
        """Test creating a ToolCallInfo."""
        tc = ToolCallInfo(
            tool_id="tool-1",
            tool_name="web_search",
            is_mcp=True,
            input_params={"query": "test"},
            status=ToolCallStatus.PENDING.value,
        )
        assert tc.tool_id == "tool-1"
        assert tc.tool_name == "web_search"
        assert tc.is_mcp is True
        assert tc.input_params == {"query": "test"}
        assert tc.status == "pending"

    def test_tool_call_to_dict(self):
        """Test ToolCallInfo serialization."""
        now = datetime.now()
        tc = ToolCallInfo(
            tool_id="tool-1",
            tool_name="web_search",
            is_mcp=False,
            input_params={"query": "test"},
            status=ToolCallStatus.COMPLETED.value,
            result={"data": "result"},
            started_at=now,
            completed_at=now,
            duration_ms=100,
        )
        data = tc.to_dict()
        assert data["tool_id"] == "tool-1"
        assert data["started_at"] == now.isoformat()
        assert data["duration_ms"] == 100

    def test_tool_call_from_dict(self):
        """Test ToolCallInfo deserialization."""
        data = {
            "tool_id": "tool-1",
            "tool_name": "web_search",
            "is_mcp": True,
            "input_params": {"query": "test"},
            "status": "completed",
            "started_at": "2024-01-01T12:00:00",
            "completed_at": "2024-01-01T12:00:01",
        }
        tc = ToolCallInfo.from_dict(data)
        assert tc.tool_id == "tool-1"
        assert isinstance(tc.started_at, datetime)


class TestThinkingContent:
    """Test ThinkingContent dataclass."""

    def test_create_thinking(self):
        """Test creating ThinkingContent."""
        now = datetime.now()
        tc = ThinkingContent(
            content="Analyzing the problem...",
            timestamp=now,
            token_count=50,
        )
        assert tc.content == "Analyzing the problem..."
        assert tc.timestamp == now
        assert tc.token_count == 50

    def test_thinking_to_dict(self):
        """Test ThinkingContent serialization."""
        now = datetime.now()
        tc = ThinkingContent(content="Test", timestamp=now)
        data = tc.to_dict()
        assert data["content"] == "Test"
        assert data["timestamp"] == now.isoformat()

    def test_thinking_from_dict(self):
        """Test ThinkingContent deserialization."""
        data = {
            "content": "Thinking...",
            "timestamp": "2024-01-01T12:00:00",
            "token_count": 100,
        }
        tc = ThinkingContent.from_dict(data)
        assert tc.content == "Thinking..."
        assert isinstance(tc.timestamp, datetime)
        assert tc.token_count == 100


class TestWorkerMessage:
    """Test WorkerMessage dataclass."""

    def test_create_message(self):
        """Test creating WorkerMessage."""
        now = datetime.now()
        msg = WorkerMessage(
            role="assistant",
            content="Hello!",
            timestamp=now,
        )
        assert msg.role == "assistant"
        assert msg.content == "Hello!"
        assert msg.timestamp == now

    def test_message_to_dict(self):
        """Test WorkerMessage serialization."""
        now = datetime.now()
        msg = WorkerMessage(role="user", content="Hi", timestamp=now)
        data = msg.to_dict()
        assert data["role"] == "user"
        assert data["timestamp"] == now.isoformat()

    def test_message_from_dict(self):
        """Test WorkerMessage deserialization."""
        data = {
            "role": "assistant",
            "content": "Response",
            "timestamp": "2024-01-01T12:00:00",
        }
        msg = WorkerMessage.from_dict(data)
        assert msg.role == "assistant"
        assert isinstance(msg.timestamp, datetime)


class TestWorkerExecution:
    """Test WorkerExecution dataclass."""

    def test_create_worker(self):
        """Test creating WorkerExecution."""
        worker = WorkerExecution(
            worker_id="worker-1",
            worker_name="Research Agent",
            worker_type=WorkerType.RESEARCH,
            role="Data Gatherer",
            status=WorkerStatus.RUNNING,
            progress=50,
        )
        assert worker.worker_id == "worker-1"
        assert worker.worker_name == "Research Agent"
        assert worker.worker_type == WorkerType.RESEARCH
        assert worker.status == WorkerStatus.RUNNING
        assert worker.progress == 50

    def test_worker_to_dict(self):
        """Test WorkerExecution serialization."""
        now = datetime.now()
        worker = WorkerExecution(
            worker_id="w-1",
            worker_name="Agent",
            worker_type=WorkerType.WRITER,
            role="Writer",
            status=WorkerStatus.COMPLETED,
            progress=100,
            started_at=now,
            completed_at=now,
        )
        data = worker.to_dict()
        assert data["worker_id"] == "w-1"
        assert data["worker_type"] == "writer"
        assert data["status"] == "completed"
        assert data["started_at"] == now.isoformat()

    def test_worker_from_dict(self):
        """Test WorkerExecution deserialization."""
        data = {
            "worker_id": "w-1",
            "worker_name": "Agent",
            "worker_type": "research",
            "role": "Researcher",
            "status": "running",
            "progress": 30,
            "tool_calls": [],
            "thinking_contents": [],
            "messages": [],
        }
        worker = WorkerExecution.from_dict(data)
        assert worker.worker_id == "w-1"
        assert worker.worker_type == WorkerType.RESEARCH
        assert worker.status == WorkerStatus.RUNNING

    def test_worker_tool_calls_count(self):
        """Test tool calls count methods."""
        worker = WorkerExecution(
            worker_id="w-1",
            worker_name="Agent",
            worker_type=WorkerType.CUSTOM,
            role="Worker",
            status=WorkerStatus.RUNNING,
            tool_calls=[
                ToolCallInfo(
                    tool_id="t1",
                    tool_name="tool1",
                    is_mcp=False,
                    input_params={},
                    status=ToolCallStatus.COMPLETED.value,
                ),
                ToolCallInfo(
                    tool_id="t2",
                    tool_name="tool2",
                    is_mcp=False,
                    input_params={},
                    status=ToolCallStatus.RUNNING.value,
                ),
            ],
        )
        assert worker.get_tool_calls_count() == 2
        assert worker.get_completed_tool_calls_count() == 1


class TestAgentSwarmStatus:
    """Test AgentSwarmStatus dataclass."""

    def test_create_swarm(self):
        """Test creating AgentSwarmStatus."""
        now = datetime.now()
        swarm = AgentSwarmStatus(
            swarm_id="swarm-1",
            mode=SwarmMode.PARALLEL,
            status=SwarmStatus.RUNNING,
            overall_progress=25,
            workers=[],
            total_tool_calls=0,
            completed_tool_calls=0,
            started_at=now,
        )
        assert swarm.swarm_id == "swarm-1"
        assert swarm.mode == SwarmMode.PARALLEL
        assert swarm.status == SwarmStatus.RUNNING
        assert swarm.overall_progress == 25

    def test_swarm_to_dict(self):
        """Test AgentSwarmStatus serialization."""
        now = datetime.now()
        swarm = AgentSwarmStatus(
            swarm_id="swarm-1",
            mode=SwarmMode.SEQUENTIAL,
            status=SwarmStatus.COMPLETED,
            overall_progress=100,
            workers=[],
            total_tool_calls=5,
            completed_tool_calls=5,
            started_at=now,
            completed_at=now,
        )
        data = swarm.to_dict()
        assert data["swarm_id"] == "swarm-1"
        assert data["mode"] == "sequential"
        assert data["status"] == "completed"

    def test_swarm_from_dict(self):
        """Test AgentSwarmStatus deserialization."""
        data = {
            "swarm_id": "s-1",
            "mode": "parallel",
            "status": "running",
            "overall_progress": 50,
            "workers": [],
            "total_tool_calls": 3,
            "completed_tool_calls": 1,
            "started_at": "2024-01-01T12:00:00",
        }
        swarm = AgentSwarmStatus.from_dict(data)
        assert swarm.swarm_id == "s-1"
        assert swarm.mode == SwarmMode.PARALLEL
        assert swarm.status == SwarmStatus.RUNNING

    def test_swarm_json_serialization(self):
        """Test JSON round-trip serialization."""
        now = datetime.now()
        original = AgentSwarmStatus(
            swarm_id="swarm-1",
            mode=SwarmMode.HIERARCHICAL,
            status=SwarmStatus.RUNNING,
            overall_progress=75,
            workers=[
                WorkerExecution(
                    worker_id="w-1",
                    worker_name="Agent 1",
                    worker_type=WorkerType.RESEARCH,
                    role="Researcher",
                    status=WorkerStatus.COMPLETED,
                    progress=100,
                )
            ],
            total_tool_calls=2,
            completed_tool_calls=2,
            started_at=now,
        )
        json_str = original.to_json()
        restored = AgentSwarmStatus.from_json(json_str)
        assert restored.swarm_id == original.swarm_id
        assert restored.mode == original.mode
        assert len(restored.workers) == 1
        assert restored.workers[0].worker_id == "w-1"

    def test_swarm_get_worker_by_id(self):
        """Test getting worker by ID."""
        now = datetime.now()
        swarm = AgentSwarmStatus(
            swarm_id="s-1",
            mode=SwarmMode.PARALLEL,
            status=SwarmStatus.RUNNING,
            overall_progress=50,
            workers=[
                WorkerExecution(
                    worker_id="w-1",
                    worker_name="Agent 1",
                    worker_type=WorkerType.RESEARCH,
                    role="R1",
                    status=WorkerStatus.RUNNING,
                ),
                WorkerExecution(
                    worker_id="w-2",
                    worker_name="Agent 2",
                    worker_type=WorkerType.WRITER,
                    role="R2",
                    status=WorkerStatus.PENDING,
                ),
            ],
            total_tool_calls=0,
            completed_tool_calls=0,
            started_at=now,
        )
        w1 = swarm.get_worker_by_id("w-1")
        assert w1 is not None
        assert w1.worker_name == "Agent 1"

        w3 = swarm.get_worker_by_id("w-3")
        assert w3 is None

    def test_swarm_get_active_workers(self):
        """Test getting active workers."""
        now = datetime.now()
        swarm = AgentSwarmStatus(
            swarm_id="s-1",
            mode=SwarmMode.PARALLEL,
            status=SwarmStatus.RUNNING,
            overall_progress=50,
            workers=[
                WorkerExecution(
                    worker_id="w-1",
                    worker_name="Agent 1",
                    worker_type=WorkerType.RESEARCH,
                    role="R1",
                    status=WorkerStatus.RUNNING,
                ),
                WorkerExecution(
                    worker_id="w-2",
                    worker_name="Agent 2",
                    worker_type=WorkerType.WRITER,
                    role="R2",
                    status=WorkerStatus.COMPLETED,
                ),
                WorkerExecution(
                    worker_id="w-3",
                    worker_name="Agent 3",
                    worker_type=WorkerType.REVIEWER,
                    role="R3",
                    status=WorkerStatus.THINKING,
                ),
            ],
            total_tool_calls=0,
            completed_tool_calls=0,
            started_at=now,
        )
        active = swarm.get_active_workers()
        assert len(active) == 2
        assert all(w.status in {WorkerStatus.RUNNING, WorkerStatus.THINKING, WorkerStatus.TOOL_CALLING} for w in active)
