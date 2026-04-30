"""Result Synthesiser — LLM-powered aggregation of multi-worker results.

When the Orchestrator dispatches tasks to multiple workers (MAF, Claude,
Swarm), their results need to be synthesised into a coherent user-facing
response.  This module provides that LLM-driven synthesis.

Sprint 114 — Phase 37 E2E Assembly B.
"""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.hybrid.orchestrator.task_result_protocol import (
    TaskResultEnvelope,
    WorkerResult,
)

logger = logging.getLogger(__name__)

_SYNTHESIS_PROMPT_TEMPLATE = """你是 IPA Platform 的結果整合助手。以下是多個 Worker 對用戶任務的執行結果。
請將這些結果整合成一個連貫、完整的回應給用戶。

## 任務背景
{task_context}

## Worker 結果
{worker_results_text}

## 整合要求
1. 合併所有 Worker 的有效輸出為一個統一回應
2. 如果有 Worker 失敗，說明哪些部分未完成
3. 保持專業語調，用繁體中文回應
4. 如果結果包含技術操作細節，用結構化格式呈現

請直接回應用戶，不需要提及 Worker 的技術細節。"""


class ResultSynthesiser:
    """Aggregates multiple worker results into a final user response.

    For single-worker results, the output is passed through directly.
    For multi-worker results, an LLM is called to produce a coherent
    synthesis.

    Args:
        llm_service: Optional LLM service for multi-result synthesis.
    """

    def __init__(self, llm_service: Any = None) -> None:
        self._llm_service = llm_service

    async def synthesise(
        self,
        envelope: TaskResultEnvelope,
        task_context: str = "",
    ) -> str:
        """Produce a final response from a TaskResultEnvelope.

        Args:
            envelope: The envelope containing all worker results.
            task_context: Optional user request context for the synthesis prompt.

        Returns:
            A synthesised response string.
        """
        if envelope.worker_count == 0:
            return "任務已記錄，但尚無執行結果。"

        # Single worker — pass through directly
        if envelope.worker_count == 1:
            result = envelope.worker_results[0]
            return self._format_single_result(result)

        # Multiple workers — synthesise with LLM
        if self._llm_service is not None:
            return await self._llm_synthesis(envelope, task_context)

        # Fallback: structured concatenation without LLM
        return self._fallback_synthesis(envelope)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_single_result(result: WorkerResult) -> str:
        """Format a single worker result for direct pass-through."""
        if result.error:
            return f"執行遇到問題：{result.error}"

        if isinstance(result.output, str):
            return result.output
        if isinstance(result.output, dict):
            # Extract meaningful content from dict
            content = result.output.get("content") or result.output.get("result")
            if content:
                return str(content)
            return str(result.output)
        if result.output is not None:
            return str(result.output)
        return "任務已完成。"

    async def _llm_synthesis(
        self,
        envelope: TaskResultEnvelope,
        task_context: str,
    ) -> str:
        """Use LLM to synthesise multiple worker results."""
        worker_texts: List[str] = []
        for i, result in enumerate(envelope.worker_results, 1):
            status_label = "✅ 成功" if result.error is None else f"❌ 失敗: {result.error}"
            output_text = str(result.output) if result.output else "(無輸出)"
            worker_texts.append(
                f"### Worker {i}: {result.worker_name} ({result.worker_type.value})\n"
                f"狀態: {status_label}\n"
                f"輸出:\n{output_text}"
            )

        prompt = _SYNTHESIS_PROMPT_TEMPLATE.format(
            task_context=task_context or "(無額外背景)",
            worker_results_text="\n\n".join(worker_texts),
        )

        try:
            response = await self._llm_service.generate(
                prompt=prompt,
                max_tokens=1024,
                temperature=0.3,
            )
            envelope.synthesised_response = response
            return response
        except Exception as e:
            logger.error("LLM synthesis failed: %s", e, exc_info=True)
            return self._fallback_synthesis(envelope)

    @staticmethod
    def _fallback_synthesis(envelope: TaskResultEnvelope) -> str:
        """Structured concatenation when LLM is not available."""
        parts: List[str] = []
        parts.append(f"收到 {envelope.worker_count} 個 Worker 的執行結果：\n")

        for i, result in enumerate(envelope.worker_results, 1):
            status = "成功" if result.error is None else f"失敗 ({result.error})"
            output = str(result.output)[:200] if result.output else "(無輸出)"
            parts.append(
                f"**{result.worker_name}** [{status}]: {output}"
            )

        if envelope.overall_status.value != "success":
            parts.append(
                f"\n⚠️ 部分 Worker 執行失敗，整體狀態: {envelope.overall_status.value}"
            )

        envelope.synthesised_response = "\n".join(parts)
        return envelope.synthesised_response
