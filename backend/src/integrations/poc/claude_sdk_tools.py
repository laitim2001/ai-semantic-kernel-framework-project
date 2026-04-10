"""SDK Tools — @tool wrappers for deep analysis capabilities.

These tools allow MAF Agents (in GroupChat/ConcurrentBuilder) to
invoke LLM for deep agentic operations:
- Deep analysis and reasoning
- Diagnostic command simulation
- Knowledge base search

Supports both Azure OpenAI and Anthropic Claude as providers.

Usage:
    tools = create_claude_sdk_tools(provider="azure")  # Azure GPT-5-mini
    tools = create_claude_sdk_tools(provider="anthropic")  # Claude Haiku
    agent = Agent(client, name="Expert", tools=[*team_tools, *tools])

PoC: Agent Team — poc/agent-team branch.
"""

import logging
import os
from typing import Optional

from agent_framework import tool

logger = logging.getLogger(__name__)


def _call_azure_openai(prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> str:
    """Call Azure OpenAI API directly for SDK tool operations."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )

    deployment = os.getenv("AZURE_OPENAI_SDK_TOOLS_DEPLOYMENT", "gpt-5-mini")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Note: gpt-5-nano only supports default temperature (1)
    create_kwargs = {
        "model": deployment,
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }
    if "nano" not in deployment:
        create_kwargs["temperature"] = 0.3
    response = client.chat.completions.create(**create_kwargs)

    content = response.choices[0].message.content or ""
    usage = response.usage
    logger.info(
        f"Azure SDK tool completed: model={deployment}, "
        f"input={usage.prompt_tokens}, output={usage.completion_tokens}"
    )
    return content


def _call_anthropic(prompt: str, system_prompt: str = "", max_tokens: int = 1024,
                    model: str = "claude-haiku-4-5-20251001", api_key: str = "") -> str:
    """Call Anthropic Claude API via ClaudeSDKClient."""
    import asyncio
    import concurrent.futures
    from src.integrations.claude_sdk.client import ClaudeSDKClient

    client = ClaudeSDKClient(
        api_key=api_key,
        model=model,
        max_completion_tokens=max_tokens,
        timeout=60,
        system_prompt=system_prompt or None,
    )

    def _run():
        return asyncio.run(client.query(prompt=prompt, max_tokens=max_tokens, timeout=60))

    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = pool.submit(_run).result(timeout=65)

    content = getattr(result, "content", None) or str(result)
    return content


def create_claude_sdk_tools(
    provider: str = "azure",
    model: str = "gpt-5-mini",
    api_key: Optional[str] = None,
) -> list:
    """Create MAF FunctionTool wrappers for SDK tool operations.

    Args:
        provider: "azure" or "anthropic"
        model: Model name (used for anthropic provider)
        api_key: API key (used for anthropic provider, reads from env if not set)
    """
    _provider = provider
    _model = model
    _api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def _call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> str:
        if _provider == "azure":
            return _call_azure_openai(prompt, system_prompt, max_tokens)
        else:
            return _call_anthropic(prompt, system_prompt, max_tokens, _model, _api_key)

    @tool(name="deep_analysis", description=(
        "Perform deep analysis with full agentic capabilities. "
        "Use this for complex tasks that require reasoning, multi-step analysis, "
        "or synthesizing information from multiple sources. "
        "Provide a clear, specific task description."
    ))
    def deep_analysis(task: str) -> str:
        """Run a deep analysis task."""
        try:
            content = _call_llm(task, max_tokens=2048)
            logger.info(f"SDK deep_analysis completed: {len(content)} chars")
            return content[:1000]
        except Exception as e:
            logger.error(f"SDK deep_analysis failed: {e}")
            return f"Analysis failed: {str(e)[:200]}"

    @tool(name="run_diagnostic_command", description=(
        "Execute a diagnostic command or script. "
        "Use this when you need to run system commands, check service status, "
        "or execute diagnostic scripts. Describe what you want to check."
    ))
    def run_diagnostic_command(command_description: str) -> str:
        """Run a diagnostic with command capabilities."""
        try:
            content = _call_llm(
                prompt=f"Run diagnostic: {command_description}",
                system_prompt=(
                    "You are a diagnostic tool. Simulate running the requested diagnostic "
                    "and provide realistic results. Format output as a command result."
                ),
                max_tokens=1024,
            )
            logger.info(f"SDK diagnostic completed: {len(content)} chars")
            return content[:800]
        except Exception as e:
            logger.error(f"SDK diagnostic failed: {e}")
            return f"Diagnostic failed: {str(e)[:200]}"

    @tool(name="search_knowledge_base", description=(
        "Search the organization's knowledge base for relevant information. "
        "Use this to find SOPs, past incident reports, system documentation, "
        "or configuration details. Provide specific search terms."
    ))
    def search_knowledge_base(query: str) -> str:
        """Search knowledge base for RAG-like retrieval."""
        try:
            content = _call_llm(
                prompt=f"Search knowledge base for: {query}",
                system_prompt=(
                    "You are a knowledge base search engine for an IT operations team. "
                    "When asked a query, provide relevant information as if searching "
                    "through incident reports, SOPs, and system documentation. "
                    "Include specific details, dates, and references."
                ),
                max_tokens=1024,
            )
            logger.info(f"SDK KB search completed: {len(content)} chars")
            return content[:800]
        except Exception as e:
            logger.error(f"SDK KB search failed: {e}")
            return f"Search failed: {str(e)[:200]}"

    return [deep_analysis, run_diagnostic_command, search_knowledge_base]
