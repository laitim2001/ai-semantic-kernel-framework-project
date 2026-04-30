"""
DirectAnswerExecutor — Inline LLM streaming response.

For simple Q&A, low-risk queries that don't need agent teams.
Streams response text via TEXT_DELTA SSE events.

Phase 45: Orchestration Core (Sprint 155)
"""

import asyncio
import logging
import os
import time
from typing import Any, Optional

from ..models import DispatchRequest, DispatchResult, ExecutionRoute
from .base import BaseExecutor

logger = logging.getLogger(__name__)


class DirectAnswerExecutor(BaseExecutor):
    """Execute simple queries with a direct LLM response.

    Uses a single LLM call with the full pipeline context as system prompt.
    Emits TEXT_DELTA events for frontend streaming.
    """

    def __init__(self, llm_client: Optional[Any] = None, model: Optional[str] = None):
        self._llm_client = llm_client
        self._model = model

    @property
    def name(self) -> str:
        return "direct_answer"

    async def _execute(
        self,
        request: DispatchRequest,
        event_queue: Optional[asyncio.Queue] = None,
    ) -> DispatchResult:
        start = time.time()

        try:
            client = self._get_client()
            system_prompt = self._build_system_prompt(request)

            response = client.chat.completions.create(
                model=self._model or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.task},
                ],
                max_completion_tokens=2048,
                temperature=0.7,
                stream=True,
            )

            full_text = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    full_text += delta

                    if event_queue is not None:
                        from ...pipeline.service import PipelineEvent, PipelineEventType

                        await event_queue.put(
                            PipelineEvent(
                                PipelineEventType.TEXT_DELTA,
                                {"content": delta},
                                step_name="dispatch",
                            )
                        )

            return DispatchResult(
                route=ExecutionRoute.DIRECT_ANSWER,
                response_text=full_text,
                duration_ms=(time.time() - start) * 1000,
                status="completed",
            )

        except Exception as e:
            logger.error("DirectAnswerExecutor failed: %s", str(e)[:200])
            return DispatchResult(
                route=ExecutionRoute.DIRECT_ANSWER,
                response_text=f"Error generating response: {str(e)[:200]}",
                duration_ms=(time.time() - start) * 1000,
                status="failed",
            )

    @staticmethod
    def _build_system_prompt(request: DispatchRequest) -> str:
        parts = [
            "You are a helpful IT Operations assistant. Answer the user's question directly.",
        ]
        if request.memory_text:
            parts.append(f"\n## User Context\n{request.memory_text[:1000]}")
        if request.knowledge_text:
            parts.append(f"\n## Knowledge Base\n{request.knowledge_text[:1000]}")
        return "\n".join(parts)

    def _get_client(self) -> Any:
        if self._llm_client is not None:
            return self._llm_client

        from openai import AzureOpenAI

        self._llm_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        )
        return self._llm_client
