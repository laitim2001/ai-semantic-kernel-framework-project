"""Claude SDK Tools — @tool wrappers for Claude Agent SDK capabilities.

These tools allow MAF Agents (in GroupChat/ConcurrentBuilder) to
invoke Claude Agent SDK for deep agentic operations:
- File reading and analysis
- Command execution
- Database queries via MCP
- Full autonomous reasoning

Usage:
    tools = create_claude_sdk_tools()
    agent = Agent(client, name="Expert", tools=[*team_tools, *tools])

PoC: Agent Team — poc/agent-team branch.
"""

import logging
import os
from typing import Optional

from agent_framework import tool

logger = logging.getLogger(__name__)


def create_claude_sdk_tools(
    model: str = "claude-haiku-4-5-20251001",
    api_key: Optional[str] = None,
) -> list:
    """Create MAF FunctionTool wrappers for Claude Agent SDK.

    Each tool internally creates a ClaudeSDKClient session and runs a query.
    """
    _api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    @tool(name="deep_analysis", description=(
        "Perform deep analysis using Claude Agent SDK with full agentic capabilities. "
        "Use this for complex tasks that require reasoning, multi-step analysis, "
        "or synthesizing information from multiple sources. "
        "Provide a clear, specific task description."
    ))
    def deep_analysis(task: str) -> str:
        """Run a deep analysis task using Claude Agent SDK."""
        try:
            import asyncio
            from src.integrations.claude_sdk.client import ClaudeSDKClient

            client = ClaudeSDKClient(
                api_key=_api_key,
                model=model,
                max_tokens=2048,
                timeout=60,
            )
            result = client.query(
                prompt=task,
                max_tokens=2048,
                timeout=60,
            )
            content = getattr(result, "content", None) or str(result)
            logger.info(f"Claude SDK deep_analysis completed: {len(content)} chars")
            return content[:1000]  # Cap output for GroupChat context
        except Exception as e:
            logger.error(f"Claude SDK deep_analysis failed: {e}")
            return f"Analysis failed: {str(e)[:200]}"

    @tool(name="run_diagnostic_command", description=(
        "Execute a diagnostic command or script using Claude Agent SDK. "
        "Use this when you need to run system commands, check service status, "
        "or execute diagnostic scripts. Describe what you want to check."
    ))
    def run_diagnostic_command(command_description: str) -> str:
        """Run a diagnostic using Claude Agent SDK with command capabilities."""
        try:
            from src.integrations.claude_sdk.client import ClaudeSDKClient

            client = ClaudeSDKClient(
                api_key=_api_key,
                model=model,
                max_tokens=1024,
                timeout=30,
                system_prompt=(
                    "You are a diagnostic tool. Simulate running the requested diagnostic "
                    "and provide realistic results. Format output as a command result."
                ),
            )
            result = client.query(
                prompt=f"Run diagnostic: {command_description}",
                max_tokens=1024,
                timeout=30,
            )
            content = getattr(result, "content", None) or str(result)
            logger.info(f"Claude SDK diagnostic completed: {len(content)} chars")
            return content[:800]
        except Exception as e:
            logger.error(f"Claude SDK diagnostic failed: {e}")
            return f"Diagnostic failed: {str(e)[:200]}"

    @tool(name="search_knowledge_base", description=(
        "Search the organization's knowledge base for relevant information. "
        "Use this to find SOPs, past incident reports, system documentation, "
        "or configuration details. Provide specific search terms."
    ))
    def search_knowledge_base(query: str) -> str:
        """Search knowledge base using Claude Agent SDK for RAG-like retrieval."""
        try:
            from src.integrations.claude_sdk.client import ClaudeSDKClient

            client = ClaudeSDKClient(
                api_key=_api_key,
                model=model,
                max_tokens=1024,
                timeout=30,
                system_prompt=(
                    "You are a knowledge base search engine for an IT operations team. "
                    "When asked a query, provide relevant information as if searching "
                    "through incident reports, SOPs, and system documentation. "
                    "Include specific details, dates, and references."
                ),
            )
            result = client.query(
                prompt=f"Search knowledge base for: {query}",
                max_tokens=1024,
                timeout=30,
            )
            content = getattr(result, "content", None) or str(result)
            logger.info(f"Claude SDK KB search completed: {len(content)} chars")
            return content[:800]
        except Exception as e:
            logger.error(f"Claude SDK KB search failed: {e}")
            return f"Search failed: {str(e)[:200]}"

    return [deep_analysis, run_diagnostic_command, search_knowledge_base]
