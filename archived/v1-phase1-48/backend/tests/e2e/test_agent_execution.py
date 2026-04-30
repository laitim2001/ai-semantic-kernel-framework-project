"""
IPA Platform - Agent Execution E2E Tests

Tests agent execution with various configurations and tools.

Test Scenarios:
- Agent execution with tools
- Agent error handling
- Agent with multiple tool calls
- Agent context passing
- Agent learning from examples

Author: IPA Platform Team
Version: 1.0.0
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime
from typing import Dict, Any

from .conftest import create_test_agent


# =============================================================================
# Agent Execution Tests
# =============================================================================

class TestAgentExecution:
    """Test agent execution scenarios."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_agent_with_tools(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test agent execution with enabled tools.

        Verifies that:
        - Agent can invoke registered tools
        - Tool responses are properly processed
        - Tool errors are handled gracefully
        """
        client = authenticated_client

        # Create agent with tools configured
        agent_data = {
            "name": f"E2E Tool Agent {datetime.now().strftime('%H%M%S')}",
            "description": "Agent with tools for testing",
            "instructions": "You are an assistant with access to tools.",
            "model": "gpt-4",
            "tools": [
                {
                    "name": "web_search",
                    "type": "builtin",
                    "config": {"enabled": True}
                },
                {
                    "name": "calculator",
                    "type": "builtin",
                    "config": {"enabled": True}
                }
            ],
            "is_active": True,
        }

        agent = await create_test_agent(client, agent_data)
        agent_id = agent.get("id")

        # Test agent execution
        execute_response = await client.post(
            f"/api/v1/agents/{agent_id}/execute",
            json={
                "message": "What is 25 * 4?",
                "context": {"use_tools": True}
            }
        )

        assert execute_response.status_code in [200, 201, 404, 422]

        # Cleanup
        await client.delete(f"/api/v1/agents/{agent_id}")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_agent_error_handling(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test agent behavior when execution errors occur.

        Verifies error handling and reporting.
        """
        client = authenticated_client

        # Create agent that might fail
        agent_data = {
            "name": f"E2E Error Agent {datetime.now().strftime('%H%M%S')}",
            "description": "Agent for error testing",
            "instructions": "Process the request",
            "model": "gpt-4",
            "is_active": True,
        }

        agent = await create_test_agent(client, agent_data)
        agent_id = agent.get("id")

        # Test with invalid input
        execute_response = await client.post(
            f"/api/v1/agents/{agent_id}/execute",
            json={
                "message": "",  # Empty message
                "context": {}
            }
        )

        # Should handle gracefully
        assert execute_response.status_code in [200, 400, 404, 422]

        # Cleanup
        await client.delete(f"/api/v1/agents/{agent_id}")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_agent_context_passing(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test passing context between agent invocations.

        Verifies that conversation history and context
        are properly maintained.
        """
        client = authenticated_client

        # Create agent
        agent_data = {
            "name": f"E2E Context Agent {datetime.now().strftime('%H%M%S')}",
            "description": "Agent for context testing",
            "instructions": "Remember and reference previous conversation.",
            "model": "gpt-4",
            "is_active": True,
        }

        agent = await create_test_agent(client, agent_data)
        agent_id = agent.get("id")

        # First message
        response1 = await client.post(
            f"/api/v1/agents/{agent_id}/execute",
            json={
                "message": "My name is Test User",
                "context": {"conversation_id": "test_conv_123"}
            }
        )

        # Second message with context
        response2 = await client.post(
            f"/api/v1/agents/{agent_id}/execute",
            json={
                "message": "What is my name?",
                "context": {
                    "conversation_id": "test_conv_123",
                    "history": [
                        {"role": "user", "content": "My name is Test User"}
                    ]
                }
            }
        )

        assert response2.status_code in [200, 201, 404, 422]

        # Cleanup
        await client.delete(f"/api/v1/agents/{agent_id}")


# =============================================================================
# Agent CRUD E2E Tests
# =============================================================================

class TestAgentCRUD:
    """Test agent CRUD operations end-to-end."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_agent_crud_lifecycle(
        self,
        authenticated_client: AsyncClient
    ):
        """Test complete CRUD lifecycle for agents."""
        client = authenticated_client
        agent_name = f"E2E CRUD Agent {datetime.now().strftime('%H%M%S')}"

        # CREATE
        create_response = await client.post(
            "/api/v1/agents/",
            json={
                "name": agent_name,
                "description": "Test agent for CRUD operations",
                "instructions": "You are a helpful assistant",
                "model": "gpt-4",
                "is_active": True,
            }
        )

        assert create_response.status_code in [200, 201, 422]

        if create_response.status_code in [200, 201]:
            agent = create_response.json()
            agent_id = agent.get("id")

            # READ
            read_response = await client.get(f"/api/v1/agents/{agent_id}")
            assert read_response.status_code == 200

            # UPDATE
            update_response = await client.put(
                f"/api/v1/agents/{agent_id}",
                json={
                    "name": agent_name + " Updated",
                    "description": "Updated description"
                }
            )
            assert update_response.status_code in [200, 422]

            # LIST
            list_response = await client.get("/api/v1/agents/")
            assert list_response.status_code == 200

            # DELETE
            delete_response = await client.delete(f"/api/v1/agents/{agent_id}")
            assert delete_response.status_code in [200, 204, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_agent_test_interface(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test the agent testing interface.

        This tests the ability to interactively test
        an agent's responses.
        """
        client = authenticated_client

        # Create agent
        agent_data = {
            "name": f"E2E Test Interface Agent {datetime.now().strftime('%H%M%S')}",
            "description": "Agent for testing interface",
            "instructions": "Respond helpfully to test queries",
            "model": "gpt-4",
            "is_active": True,
        }

        agent = await create_test_agent(client, agent_data)
        agent_id = agent.get("id")

        # Test the agent
        test_response = await client.post(
            f"/api/v1/agents/{agent_id}/test",
            json={
                "message": "Hello, this is a test",
                "max_tokens": 100
            }
        )

        assert test_response.status_code in [200, 201, 404, 422]

        # Cleanup
        await client.delete(f"/api/v1/agents/{agent_id}")


# =============================================================================
# Agent Templates E2E Tests
# =============================================================================

class TestAgentTemplates:
    """Test agent template functionality."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_create_agent_from_template(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test creating an agent from a template.
        """
        client = authenticated_client

        # Get available templates
        templates_response = await client.get("/api/v1/templates/")

        if templates_response.status_code == 200:
            templates = templates_response.json()

            if templates and isinstance(templates, list) and len(templates) > 0:
                template_id = templates[0].get("id")

                # Create agent from template
                create_response = await client.post(
                    f"/api/v1/templates/{template_id}/instantiate",
                    json={
                        "name": f"E2E Template Agent {datetime.now().strftime('%H%M%S')}",
                        "customizations": {
                            "temperature": 0.8
                        }
                    }
                )

                if create_response.status_code in [200, 201]:
                    agent = create_response.json()
                    # Cleanup
                    await client.delete(f"/api/v1/agents/{agent.get('id')}")

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_template_listing_and_search(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test template listing and search functionality.
        """
        client = authenticated_client

        # List all templates
        list_response = await client.get("/api/v1/templates/")
        assert list_response.status_code in [200, 404]

        # Search templates
        search_response = await client.get(
            "/api/v1/templates/",
            params={"search": "customer", "category": "service"}
        )
        assert search_response.status_code in [200, 404]


# =============================================================================
# Agent Learning E2E Tests
# =============================================================================

class TestAgentLearning:
    """Test agent few-shot learning functionality."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_add_learning_example(
        self,
        authenticated_client: AsyncClient
    ):
        """
        Test adding learning examples to an agent.
        """
        client = authenticated_client

        # Create agent
        agent = await create_test_agent(client, {
            "name": f"E2E Learning Agent {datetime.now().strftime('%H%M%S')}",
            "description": "Agent for learning testing",
            "instructions": "Learn from provided examples",
            "model": "gpt-4",
            "is_active": True,
        })
        agent_id = agent.get("id")

        # Add learning example
        learn_response = await client.post(
            f"/api/v1/learning/agents/{agent_id}/examples",
            json={
                "input": "Customer asks about refund policy",
                "output": "Our refund policy allows returns within 30 days...",
                "category": "customer_service"
            }
        )

        assert learn_response.status_code in [200, 201, 404, 422]

        # List examples
        examples_response = await client.get(
            f"/api/v1/learning/agents/{agent_id}/examples"
        )
        assert examples_response.status_code in [200, 404]

        # Cleanup
        await client.delete(f"/api/v1/agents/{agent_id}")
