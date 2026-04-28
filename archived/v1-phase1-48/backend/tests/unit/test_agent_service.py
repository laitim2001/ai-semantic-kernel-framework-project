# =============================================================================
# IPA Platform - Agent Service Unit Tests
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# Tests for AgentService functionality including:
#   - Service initialization
#   - Agent execution (mock mode)
#   - LLM cost calculation
#   - Error handling
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.agents.service import (
    AgentConfig,
    AgentExecutionResult,
    AgentService,
    get_agent_service,
    init_agent_service,
)


# =============================================================================
# AgentConfig Tests
# =============================================================================


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_agent_config_basic(self):
        """Test basic AgentConfig creation."""
        config = AgentConfig(
            name="test-agent",
            instructions="You are a helpful assistant.",
        )

        assert config.name == "test-agent"
        assert config.instructions == "You are a helpful assistant."
        assert config.tools == []
        assert config.model_config == {}
        assert config.max_iterations == 10

    def test_agent_config_with_tools(self):
        """Test AgentConfig with tools."""

        def sample_tool():
            pass

        config = AgentConfig(
            name="tool-agent",
            instructions="Use tools to help users.",
            tools=[sample_tool],
        )

        assert len(config.tools) == 1
        assert config.tools[0] == sample_tool

    def test_agent_config_with_model_config(self):
        """Test AgentConfig with custom model configuration."""
        config = AgentConfig(
            name="custom-agent",
            instructions="Be creative.",
            model_config={
                "temperature": 0.8,
                "max_tokens": 2000,
            },
        )

        assert config.model_config["temperature"] == 0.8
        assert config.model_config["max_tokens"] == 2000

    def test_agent_config_custom_iterations(self):
        """Test AgentConfig with custom max_iterations."""
        config = AgentConfig(
            name="limited-agent",
            instructions="Work efficiently.",
            max_iterations=5,
        )

        assert config.max_iterations == 5


# =============================================================================
# AgentExecutionResult Tests
# =============================================================================


class TestAgentExecutionResult:
    """Tests for AgentExecutionResult dataclass."""

    def test_execution_result_basic(self):
        """Test basic AgentExecutionResult creation."""
        result = AgentExecutionResult(text="Hello, world!")

        assert result.text == "Hello, world!"
        assert result.llm_calls == 0
        assert result.llm_tokens == 0
        assert result.llm_cost == 0.0
        assert result.tool_calls == []

    def test_execution_result_with_stats(self):
        """Test AgentExecutionResult with usage statistics."""
        result = AgentExecutionResult(
            text="Response text",
            llm_calls=2,
            llm_tokens=500,
            llm_cost=0.0035,
            tool_calls=[{"tool": "search", "input": {"query": "test"}}],
        )

        assert result.llm_calls == 2
        assert result.llm_tokens == 500
        assert result.llm_cost == 0.0035
        assert len(result.tool_calls) == 1


# =============================================================================
# AgentService Tests
# =============================================================================


class TestAgentService:
    """Tests for AgentService class."""

    def test_service_creation(self):
        """Test AgentService instance creation."""
        service = AgentService()

        assert not service.is_initialized
        assert service._client is None

    @pytest.mark.asyncio
    async def test_service_initialize_no_azure(self):
        """Test initialization without Azure OpenAI configured."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
                azure_openai_endpoint=None,
                azure_openai_deployment_name=None,
            )

            service = AgentService()
            await service.initialize()

            assert service.is_initialized
            assert service._client is None

    @pytest.mark.asyncio
    async def test_service_shutdown(self):
        """Test service shutdown."""
        service = AgentService()
        service._initialized = True
        service._client = MagicMock()

        await service.shutdown()

        assert not service.is_initialized
        assert service._client is None

    @pytest.mark.asyncio
    async def test_service_double_initialize(self):
        """Test that double initialization is handled gracefully."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            service = AgentService()
            await service.initialize()
            await service.initialize()  # Should not fail

            assert service.is_initialized

    def test_ensure_initialized_raises(self):
        """Test that _ensure_initialized raises when not initialized."""
        service = AgentService()

        with pytest.raises(RuntimeError, match="not initialized"):
            service._ensure_initialized()

    def test_ensure_initialized_passes(self):
        """Test that _ensure_initialized passes when initialized."""
        service = AgentService()
        service._initialized = True

        # Should not raise
        service._ensure_initialized()


# =============================================================================
# Cost Calculation Tests
# =============================================================================


class TestCostCalculation:
    """Tests for LLM cost calculation."""

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        service = AgentService()

        cost = service._calculate_cost(0, 0)

        assert cost == 0.0

    def test_calculate_cost_input_only(self):
        """Test cost calculation with only input tokens."""
        service = AgentService()

        # 1000 tokens * $5/1M = $0.005
        cost = service._calculate_cost(1000, 0)

        assert cost == pytest.approx(0.005, rel=1e-6)

    def test_calculate_cost_output_only(self):
        """Test cost calculation with only output tokens."""
        service = AgentService()

        # 1000 tokens * $15/1M = $0.015
        cost = service._calculate_cost(0, 1000)

        assert cost == pytest.approx(0.015, rel=1e-6)

    def test_calculate_cost_mixed(self):
        """Test cost calculation with both input and output tokens."""
        service = AgentService()

        # 500 input * $5/1M + 200 output * $15/1M
        # = $0.0025 + $0.003 = $0.0055 (per million)
        # Actually: (500/1M * 5) + (200/1M * 15)
        # = 0.0000025 + 0.000003 = 0.0000055
        cost = service._calculate_cost(500, 200)

        expected = (500 / 1_000_000) * 5.0 + (200 / 1_000_000) * 15.0
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_large_volume(self):
        """Test cost calculation with large token volumes."""
        service = AgentService()

        # 1 million input + 500K output
        # = $5 + $7.5 = $12.5
        cost = service._calculate_cost(1_000_000, 500_000)

        assert cost == pytest.approx(12.5, rel=1e-6)


# =============================================================================
# Mock Mode Execution Tests
# =============================================================================


class TestMockModeExecution:
    """Tests for agent execution in mock mode (no Azure OpenAI)."""

    @pytest.mark.asyncio
    async def test_run_agent_mock_mode(self):
        """Test running agent in mock mode returns mock response."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            service = AgentService()
            await service.initialize()

            config = AgentConfig(
                name="test-agent",
                instructions="You are helpful.",
            )
            result = await service.run_agent_with_config(config, "Hello")

            assert "[Mock Response]" in result.text
            assert "test-agent" in result.text
            assert "Hello" in result.text
            assert result.llm_calls == 0
            assert result.llm_tokens == 0
            assert result.llm_cost == 0.0

    @pytest.mark.asyncio
    async def test_run_simple_mock_mode(self):
        """Test run_simple in mock mode."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            service = AgentService()
            await service.initialize()

            result = await service.run_simple(
                instructions="Be helpful.",
                message="What is 2+2?",
            )

            assert "[Mock Response]" in result
            assert "simple-agent" in result

    @pytest.mark.asyncio
    async def test_run_agent_not_initialized_raises(self):
        """Test that running agent without initialization raises error."""
        service = AgentService()

        config = AgentConfig(
            name="test-agent",
            instructions="You are helpful.",
        )

        with pytest.raises(RuntimeError, match="not initialized"):
            await service.run_agent_with_config(config, "Hello")


# =============================================================================
# Global Instance Tests
# =============================================================================


class TestGlobalInstance:
    """Tests for global service instance management."""

    def test_get_agent_service_creates_instance(self):
        """Test that get_agent_service creates a new instance."""
        # Reset global instance
        import src.domain.agents.service as service_module

        service_module._agent_service = None

        service = get_agent_service()

        assert service is not None
        assert isinstance(service, AgentService)

    def test_get_agent_service_returns_singleton(self):
        """Test that get_agent_service returns the same instance."""
        service1 = get_agent_service()
        service2 = get_agent_service()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_init_agent_service(self):
        """Test init_agent_service initializes the service."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            # Reset global instance
            import src.domain.agents.service as service_module

            service_module._agent_service = None

            service = await init_agent_service()

            assert service.is_initialized


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Test handling of empty message."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            service = AgentService()
            await service.initialize()

            config = AgentConfig(
                name="test-agent",
                instructions="You are helpful.",
            )
            result = await service.run_agent_with_config(config, "")

            assert result.text is not None

    @pytest.mark.asyncio
    async def test_long_instructions(self):
        """Test handling of very long instructions."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            service = AgentService()
            await service.initialize()

            long_instructions = "Be helpful. " * 1000

            config = AgentConfig(
                name="verbose-agent",
                instructions=long_instructions,
            )
            result = await service.run_agent_with_config(config, "Hello")

            assert result.text is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_message(self):
        """Test handling of special characters in message."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            service = AgentService()
            await service.initialize()

            config = AgentConfig(
                name="test-agent",
                instructions="You are helpful.",
            )
            special_message = "Hello! 你好 مرحبا 🎉 <script>alert('xss')</script>"
            result = await service.run_agent_with_config(config, special_message)

            assert result.text is not None
            assert special_message in result.text

    @pytest.mark.asyncio
    async def test_run_with_context(self):
        """Test running agent with additional context."""
        with patch("src.domain.agents.service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_configured=False,
            )

            service = AgentService()
            await service.initialize()

            config = AgentConfig(
                name="context-agent",
                instructions="Use the provided context.",
            )
            context = {
                "user_id": "12345",
                "department": "IT",
                "priority": "high",
            }
            result = await service.run_agent_with_config(
                config, "Help me", context=context
            )

            assert result.text is not None
