"""
MAF ACL Interfaces Tests

Tests frozen dataclass immutability and ABC interface enforcement.

Sprint 128: Story 128-3
"""

import pytest
from dataclasses import FrozenInstanceError
from typing import Any, AsyncIterator, Dict, List

from src.integrations.agent_framework.acl.interfaces import (
    AgentBuilderInterface,
    AgentConfig,
    AgentRunnerInterface,
    ToolInterface,
    WorkflowResult,
)


# =============================================================================
# Frozen Dataclass Tests
# =============================================================================


class TestAgentConfigFrozen:
    """Tests for AgentConfig immutability."""

    def test_create_agent_config(self):
        """AgentConfig can be created with all fields."""
        config = AgentConfig(
            name="test-agent",
            description="A test agent",
            model="gpt-4o",
            system_prompt="You are a test agent",
            tools=("search", "calculate"),
            metadata=(("key1", "value1"),),
        )
        assert config.name == "test-agent"
        assert config.model == "gpt-4o"
        assert config.tools == ("search", "calculate")

    def test_agent_config_is_frozen(self):
        """AgentConfig fields cannot be modified after creation."""
        config = AgentConfig(name="test")
        with pytest.raises(FrozenInstanceError):
            config.name = "modified"

    def test_agent_config_defaults(self):
        """AgentConfig has correct default values."""
        config = AgentConfig(name="test")
        assert config.description == ""
        assert config.model == "gpt-4o"
        assert config.system_prompt == ""
        assert config.tools == ()
        assert config.metadata == ()

    def test_get_tools_list(self):
        """get_tools_list() returns a mutable list copy."""
        config = AgentConfig(name="test", tools=("a", "b"))
        tools = config.get_tools_list()
        assert tools == ["a", "b"]
        tools.append("c")  # Mutable copy — original unchanged
        assert config.tools == ("a", "b")

    def test_get_metadata_dict(self):
        """get_metadata_dict() returns a mutable dict copy."""
        config = AgentConfig(
            name="test",
            metadata=(("key1", "val1"), ("key2", "val2")),
        )
        meta = config.get_metadata_dict()
        assert meta == {"key1": "val1", "key2": "val2"}


class TestWorkflowResultFrozen:
    """Tests for WorkflowResult immutability."""

    def test_create_success_result(self):
        """WorkflowResult can be created for success case."""
        result = WorkflowResult(success=True, output="done")
        assert result.success is True
        assert result.output == "done"
        assert result.error is None

    def test_create_failure_result(self):
        """WorkflowResult can be created for failure case."""
        result = WorkflowResult(success=False, error="timeout")
        assert result.success is False
        assert result.error == "timeout"

    def test_workflow_result_is_frozen(self):
        """WorkflowResult fields cannot be modified after creation."""
        result = WorkflowResult(success=True)
        with pytest.raises(FrozenInstanceError):
            result.success = False

    def test_get_metadata_dict(self):
        """get_metadata_dict() returns mutable dict from frozen tuple."""
        result = WorkflowResult(
            success=True,
            metadata=(("elapsed_ms", 150), ("retry_count", 0)),
        )
        meta = result.get_metadata_dict()
        assert meta["elapsed_ms"] == 150


# =============================================================================
# ABC Interface Enforcement Tests
# =============================================================================


class TestAgentBuilderInterfaceABC:
    """Tests for AgentBuilderInterface ABC enforcement."""

    def test_cannot_instantiate_directly(self):
        """AgentBuilderInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentBuilderInterface()

    def test_concrete_implementation_works(self):
        """Concrete implementation satisfying all abstract methods works."""

        class ConcreteBuilder(AgentBuilderInterface):
            def __init__(self):
                self._agents = []

            def add_agent(self, config: AgentConfig) -> None:
                self._agents.append(config)

            def build(self) -> Any:
                return {"agents": self._agents}

            def validate(self) -> List[str]:
                if not self._agents:
                    return ["No agents added"]
                return []

        builder = ConcreteBuilder()
        builder.add_agent(AgentConfig(name="agent-1"))
        assert builder.validate() == []
        result = builder.build()
        assert len(result["agents"]) == 1


class TestAgentRunnerInterfaceABC:
    """Tests for AgentRunnerInterface ABC enforcement."""

    def test_cannot_instantiate_directly(self):
        """AgentRunnerInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentRunnerInterface()


class TestToolInterfaceABC:
    """Tests for ToolInterface ABC enforcement."""

    def test_cannot_instantiate_directly(self):
        """ToolInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ToolInterface()

    def test_concrete_tool_implementation(self):
        """Concrete tool implementation satisfying all abstract methods works."""

        class SearchTool(ToolInterface):
            def get_name(self) -> str:
                return "search"

            def get_description(self) -> str:
                return "Search the knowledge base"

            def get_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                }

            async def execute(self, **params: Any) -> Any:
                return f"Results for: {params.get('query', '')}"

        tool = SearchTool()
        assert tool.get_name() == "search"
        assert "query" in tool.get_schema()["properties"]
