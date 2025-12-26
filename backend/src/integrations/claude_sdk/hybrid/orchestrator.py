"""Hybrid Orchestrator for Microsoft Agent Framework and Claude SDK.

Sprint 50: S50-3 - Hybrid Orchestrator (12 pts)

This module provides the main orchestration logic for routing tasks
between Microsoft Agent Framework and Claude Agent SDK based on
task characteristics and capabilities.
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from .capability import CapabilityMatcher
from .selector import FrameworkSelector, SelectionContext, SelectionStrategy
from .types import (
    Framework,
    HybridResult,
    HybridSessionConfig,
    TaskAnalysis,
    TaskCapability,
    ToolCall,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for task execution."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_framework: Optional[str] = None
    tool_results: List[ToolCall] = field(default_factory=list)


class HybridOrchestrator:
    """Orchestrates task execution between MS Agent Framework and Claude SDK.

    Provides intelligent routing, context synchronization, and unified
    execution interface for hybrid AI agent systems.
    """

    def __init__(
        self,
        *,
        config: Optional[HybridSessionConfig] = None,
        capability_matcher: Optional[CapabilityMatcher] = None,
        framework_selector: Optional[FrameworkSelector] = None,
        claude_executor: Optional[Callable] = None,
        ms_executor: Optional[Callable] = None,
    ):
        """Initialize the hybrid orchestrator.

        Args:
            config: Session configuration.
            capability_matcher: Matcher for capability analysis.
            framework_selector: Selector for framework choice.
            claude_executor: Executor function for Claude SDK.
            ms_executor: Executor function for MS Agent Framework.
        """
        self._config = config or HybridSessionConfig()
        self._matcher = capability_matcher or CapabilityMatcher()
        self._selector = framework_selector or FrameworkSelector(
            capability_matcher=self._matcher,
            switch_threshold=self._config.switch_confidence_threshold,
        )

        # Executors (can be injected or use defaults)
        self._claude_executor = claude_executor
        self._ms_executor = ms_executor

        # Session state
        self._sessions: Dict[str, ExecutionContext] = {}
        self._active_session: Optional[str] = None

        # Metrics
        self._execution_count = 0
        self._total_duration = 0.0
        self._framework_usage: Dict[str, int] = {
            "claude_sdk": 0,
            "microsoft_agent_framework": 0,
        }

    @property
    def config(self) -> HybridSessionConfig:
        """Get current configuration."""
        return self._config

    @property
    def active_session_id(self) -> Optional[str]:
        """Get active session ID."""
        return self._active_session

    @property
    def session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new execution session.

        Args:
            session_id: Optional custom session ID.
            metadata: Optional session metadata.

        Returns:
            The session ID.
        """
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = ExecutionContext(
            session_id=sid,
            metadata=metadata or {},
        )
        self._active_session = sid
        logger.info(f"Created hybrid session: {sid}")
        return sid

    def get_session(self, session_id: str) -> Optional[ExecutionContext]:
        """Get a session by ID.

        Args:
            session_id: The session ID.

        Returns:
            ExecutionContext or None if not found.
        """
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        """Close and remove a session.

        Args:
            session_id: The session ID to close.

        Returns:
            True if session was closed.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session == session_id:
                self._active_session = None
            logger.info(f"Closed hybrid session: {session_id}")
            return True
        return False

    async def execute(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
        force_framework: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> HybridResult:
        """Execute a task using the optimal framework.

        Args:
            prompt: The task prompt or user message.
            session_id: Optional session ID (creates new if not provided).
            force_framework: Force specific framework.
            tools: Available tools for execution.
            max_tokens: Maximum tokens for response.
            timeout: Execution timeout in seconds.

        Returns:
            HybridResult with execution outcome.
        """
        start_time = time.time()

        # Get or create session
        if session_id and session_id in self._sessions:
            context = self._sessions[session_id]
        else:
            sid = self.create_session(session_id)
            context = self._sessions[sid]

        try:
            # Analyze task if not forcing framework
            if force_framework:
                framework = force_framework
                analysis = self._matcher.analyze(prompt)
                confidence = 0.95
            else:
                analysis = self._matcher.analyze(prompt)
                selection_ctx = SelectionContext(
                    task_analysis=analysis,
                    session_framework=context.current_framework,
                    session_message_count=len(context.conversation_history),
                    max_tokens=max_tokens,
                    timeout_seconds=timeout,
                    allow_framework_switch=self._config.auto_switch,
                )
                selection = self._selector.select(prompt, selection_ctx)
                framework = selection.framework
                confidence = selection.confidence

                # Log if switching
                if (
                    context.current_framework
                    and context.current_framework != framework
                    and selection.switch_recommended
                ):
                    logger.info(
                        f"Switching framework: {context.current_framework} → {framework}"
                    )

            # Update context
            context.current_framework = framework
            context.conversation_history.append({
                "role": "user",
                "content": prompt,
                "timestamp": time.time(),
            })

            # Execute with appropriate framework
            if framework == "microsoft_agent_framework":
                result = await self._execute_ms_agent(
                    prompt, context, tools, max_tokens, timeout
                )
            else:
                result = await self._execute_claude(
                    prompt, context, tools, max_tokens, timeout
                )

            # Update result with analysis
            result.task_analysis = analysis
            result.session_id = context.session_id

            # Add response to history
            context.conversation_history.append({
                "role": "assistant",
                "content": result.content,
                "framework": framework,
                "timestamp": time.time(),
            })

            # Update metrics
            self._execution_count += 1
            self._framework_usage[framework] += 1

        except asyncio.TimeoutError:
            result = HybridResult(
                success=False,
                error=f"Execution timed out after {timeout}s",
                framework_used=framework,
                session_id=context.session_id,
            )
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            result = HybridResult(
                success=False,
                error=str(e),
                framework_used=framework if "framework" in locals() else "unknown",
                session_id=context.session_id,
            )

        # Calculate duration
        result.duration = time.time() - start_time
        self._total_duration += result.duration

        return result

    async def _execute_claude(
        self,
        prompt: str,
        context: ExecutionContext,
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: Optional[int],
        timeout: Optional[float],
    ) -> HybridResult:
        """Execute task using Claude SDK.

        Args:
            prompt: The task prompt.
            context: Execution context.
            tools: Available tools.
            max_tokens: Token limit.
            timeout: Timeout in seconds.

        Returns:
            HybridResult from Claude execution.
        """
        if self._claude_executor:
            # Use injected executor
            try:
                raw_result = await asyncio.wait_for(
                    self._claude_executor(
                        prompt=prompt,
                        history=context.conversation_history,
                        tools=tools,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout or self._config.timeout,
                )

                # Convert to HybridResult
                if isinstance(raw_result, HybridResult):
                    return raw_result
                elif isinstance(raw_result, dict):
                    return HybridResult(
                        content=raw_result.get("content", ""),
                        framework_used="claude_sdk",
                        tokens_used=raw_result.get("tokens_used", 0),
                        input_tokens=raw_result.get("input_tokens", 0),
                        output_tokens=raw_result.get("output_tokens", 0),
                        success=True,
                    )
                else:
                    return HybridResult(
                        content=str(raw_result),
                        framework_used="claude_sdk",
                        success=True,
                    )
            except Exception as e:
                logger.error(f"Claude executor error: {e}")
                return HybridResult(
                    success=False,
                    error=str(e),
                    framework_used="claude_sdk",
                )
        else:
            # Simulated response for testing
            return HybridResult(
                content=f"[Claude SDK] Processed: {prompt[:100]}...",
                framework_used="claude_sdk",
                success=True,
            )

    async def _execute_ms_agent(
        self,
        prompt: str,
        context: ExecutionContext,
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: Optional[int],
        timeout: Optional[float],
    ) -> HybridResult:
        """Execute task using Microsoft Agent Framework.

        Args:
            prompt: The task prompt.
            context: Execution context.
            tools: Available tools.
            max_tokens: Token limit.
            timeout: Timeout in seconds.

        Returns:
            HybridResult from MS Agent execution.
        """
        if self._ms_executor:
            # Use injected executor
            try:
                raw_result = await asyncio.wait_for(
                    self._ms_executor(
                        prompt=prompt,
                        history=context.conversation_history,
                        tools=tools,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout or self._config.timeout,
                )

                # Convert to HybridResult
                if isinstance(raw_result, HybridResult):
                    return raw_result
                elif isinstance(raw_result, dict):
                    return HybridResult(
                        content=raw_result.get("content", ""),
                        framework_used="microsoft_agent_framework",
                        tokens_used=raw_result.get("tokens_used", 0),
                        input_tokens=raw_result.get("input_tokens", 0),
                        output_tokens=raw_result.get("output_tokens", 0),
                        success=True,
                    )
                else:
                    return HybridResult(
                        content=str(raw_result),
                        framework_used="microsoft_agent_framework",
                        success=True,
                    )
            except Exception as e:
                logger.error(f"MS Agent executor error: {e}")
                return HybridResult(
                    success=False,
                    error=str(e),
                    framework_used="microsoft_agent_framework",
                )
        else:
            # Simulated response for testing
            return HybridResult(
                content=f"[MS Agent Framework] Processed: {prompt[:100]}...",
                framework_used="microsoft_agent_framework",
                success=True,
            )

    async def execute_stream(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
        force_framework: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute task with streaming response.

        Args:
            prompt: The task prompt.
            session_id: Optional session ID.
            force_framework: Force specific framework.
            tools: Available tools.

        Yields:
            Response chunks as they become available.
        """
        # For now, execute and yield complete result
        # Full streaming implementation would integrate with
        # framework-specific streaming APIs
        result = await self.execute(
            prompt,
            session_id=session_id,
            force_framework=force_framework,
            tools=tools,
        )

        if result.success:
            # Simulate streaming by yielding chunks
            content = result.content
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                yield content[i:i + chunk_size]
                await asyncio.sleep(0.01)  # Small delay for streaming effect
        else:
            yield f"Error: {result.error}"

    def analyze_task(self, prompt: str) -> TaskAnalysis:
        """Analyze a task without executing.

        Args:
            prompt: The task prompt to analyze.

        Returns:
            TaskAnalysis with capability assessment.
        """
        return self._matcher.analyze(prompt)

    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics.

        Returns:
            Dictionary with execution statistics.
        """
        avg_duration = (
            self._total_duration / self._execution_count
            if self._execution_count > 0
            else 0.0
        )

        return {
            "execution_count": self._execution_count,
            "total_duration": self._total_duration,
            "avg_duration": avg_duration,
            "session_count": len(self._sessions),
            "framework_usage": dict(self._framework_usage),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._execution_count = 0
        self._total_duration = 0.0
        self._framework_usage = {
            "claude_sdk": 0,
            "microsoft_agent_framework": 0,
        }

    @asynccontextmanager
    async def session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for session lifecycle.

        Args:
            session_id: Optional session ID.
            metadata: Optional session metadata.

        Yields:
            The orchestrator with active session.
        """
        sid = self.create_session(session_id, metadata)
        try:
            yield self
        finally:
            self.close_session(sid)

    def set_claude_executor(self, executor: Callable) -> None:
        """Set the Claude SDK executor.

        Args:
            executor: Async function for Claude execution.
        """
        self._claude_executor = executor

    def set_ms_executor(self, executor: Callable) -> None:
        """Set the MS Agent Framework executor.

        Args:
            executor: Async function for MS Agent execution.
        """
        self._ms_executor = executor


def create_orchestrator(
    *,
    primary_framework: str = "claude_sdk",
    auto_switch: bool = True,
    switch_threshold: float = 0.7,
) -> HybridOrchestrator:
    """Factory function to create a HybridOrchestrator.

    Args:
        primary_framework: Default framework to use.
        auto_switch: Whether to auto-switch frameworks.
        switch_threshold: Confidence threshold for switching.

    Returns:
        Configured HybridOrchestrator instance.
    """
    config = HybridSessionConfig(
        primary_framework=primary_framework,
        auto_switch=auto_switch,
        switch_confidence_threshold=switch_threshold,
    )

    return HybridOrchestrator(config=config)
