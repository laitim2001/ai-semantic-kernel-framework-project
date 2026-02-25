"""
MAF ACL — Stable Interfaces

Defines immutable data types and abstract interfaces that form the
stable contract between IPA Platform and the MAF adapter layer.
These interfaces MUST NOT change when MAF API changes.

Sprint 128: Story 128-2 — ACL Interfaces
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional


# =============================================================================
# Immutable Data Types
# =============================================================================


@dataclass(frozen=True)
class AgentConfig:
    """
    Stable configuration for creating an agent.

    This is a frozen (immutable) dataclass — once created, values cannot change.
    Maps to MAF's agent creation parameters without depending on MAF types.

    Attributes:
        name: Agent display name
        description: Agent description/purpose
        model: LLM model identifier (e.g., "gpt-4o", "claude-3-haiku")
        system_prompt: System instructions for the agent
        tools: List of tool names available to the agent
        metadata: Additional configuration key-value pairs
    """

    name: str
    description: str = ""
    model: str = "gpt-4o"
    system_prompt: str = ""
    tools: tuple = ()  # Use tuple for immutability (frozen dataclass)
    metadata: tuple = ()  # Tuple of (key, value) pairs for immutability

    def get_tools_list(self) -> List[str]:
        """Get tools as a mutable list."""
        return list(self.tools)

    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as a mutable dictionary."""
        return dict(self.metadata)


@dataclass(frozen=True)
class WorkflowResult:
    """
    Stable result from workflow execution.

    This is a frozen (immutable) dataclass — once created, values cannot change.
    Normalizes MAF's various result types into a consistent structure.

    Attributes:
        success: Whether the workflow completed successfully
        output: The workflow output (string or serializable data)
        error: Error message if failed
        metadata: Additional result metadata
    """

    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: tuple = ()  # Tuple of (key, value) pairs for immutability

    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as a mutable dictionary."""
        return dict(self.metadata)


# =============================================================================
# Abstract Interfaces
# =============================================================================


class AgentBuilderInterface(ABC):
    """
    Stable interface for building agent workflows.

    Implementations adapt this interface to the current MAF Builder API.
    When MAF changes, only the adapter implementation changes — not this interface.

    Example:
        class MyBuilder(AgentBuilderInterface):
            def add_agent(self, config):
                self._builder.add_participant(config.name)
            def build(self):
                return self._builder.build()
    """

    @abstractmethod
    def add_agent(self, config: AgentConfig) -> None:
        """
        Add an agent to the workflow.

        Args:
            config: Agent configuration (stable type)
        """
        ...

    @abstractmethod
    def build(self) -> Any:
        """
        Build the workflow.

        Returns:
            Built workflow object (type depends on MAF version)

        Raises:
            WorkflowBuildError: If build fails
        """
        ...

    @abstractmethod
    def validate(self) -> List[str]:
        """
        Validate the current configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        ...


class AgentRunnerInterface(ABC):
    """
    Stable interface for executing agent workflows.

    Implementations adapt this interface to the current MAF execution API.

    Example:
        class MyRunner(AgentRunnerInterface):
            async def execute(self, workflow, input_data):
                result = await workflow.run(input_data)
                return WorkflowResult(success=True, output=result)
    """

    @abstractmethod
    async def execute(
        self,
        workflow: Any,
        input_data: Any,
        **kwargs: Any,
    ) -> WorkflowResult:
        """
        Execute a workflow.

        Args:
            workflow: Built workflow object (from AgentBuilderInterface.build())
            input_data: Input data for the workflow
            **kwargs: Additional execution parameters

        Returns:
            WorkflowResult with execution outcome

        Raises:
            ExecutionError: If execution fails
        """
        ...

    @abstractmethod
    async def execute_stream(
        self,
        workflow: Any,
        input_data: Any,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """
        Execute a workflow with streaming output.

        Args:
            workflow: Built workflow object
            input_data: Input data for the workflow
            **kwargs: Additional execution parameters

        Yields:
            Workflow events/chunks

        Raises:
            ExecutionError: If execution fails
        """
        ...

    @abstractmethod
    async def cancel(self, execution_id: str) -> bool:
        """
        Cancel a running workflow execution.

        Args:
            execution_id: ID of the execution to cancel

        Returns:
            True if cancellation was successful
        """
        ...


class ToolInterface(ABC):
    """
    Stable interface for agent tools.

    Implementations wrap MAF tool definitions into a stable interface.

    Example:
        class MyTool(ToolInterface):
            def get_name(self):
                return "search"
            def get_schema(self):
                return {"type": "object", "properties": {...}}
            async def execute(self, **params):
                return search_results
    """

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the tool name.

        Returns:
            Unique tool name string
        """
        ...

    @abstractmethod
    def get_description(self) -> str:
        """
        Get the tool description.

        Returns:
            Human-readable description of what the tool does
        """
        ...

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the tool's input parameter schema.

        Returns:
            JSON Schema describing the tool's parameters
        """
        ...

    @abstractmethod
    async def execute(self, **params: Any) -> Any:
        """
        Execute the tool with given parameters.

        Args:
            **params: Tool parameters matching the schema

        Returns:
            Tool execution result

        Raises:
            Exception: If tool execution fails
        """
        ...
