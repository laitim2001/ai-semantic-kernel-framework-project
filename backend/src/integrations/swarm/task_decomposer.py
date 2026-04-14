"""TaskDecomposer — LLM-powered task decomposition for Swarm execution.

Analyzes a complex user request and breaks it into independent sub-tasks,
each assigned to a specialist Worker role. Uses generate_structured()
for reliable JSON output.

Sprint 148 — Phase 43 Swarm Core Engine.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.integrations.orchestration.experts.bridge import (
    get_expert_descriptions,
    get_expert_role_names,
)

logger = logging.getLogger(__name__)

DECOMPOSE_PROMPT = """你是一個任務拆解專家。請分析以下任務，將它拆解為可獨立執行的子任務。

## 可用的專家角色
{roles}

## 專家能力詳情
{expert_details}

## 可用的工具
{tools}

## 用戶任務
{task}

## 拆解規則
1. 每個子任務必須可以獨立執行（不依賴其他子任務的結果）
2. 每個子任務分配一個最適合的專家角色
3. 子任務數量 2-5 個（太簡單的任務只需 1 個）
4. 每個子任務描述要具體、可執行
5. 如果任務很簡單，只需要一個通用助手，直接返回 1 個子任務

## 輸出格式（JSON）
{{
    "mode": "parallel",
    "reasoning": "拆解理由...",
    "sub_tasks": [
        {{
            "title": "子任務標題",
            "description": "具體描述和要求",
            "role": "角色名稱（從可用角色中選擇）",
            "priority": 1,
            "tools_needed": ["工具名稱"]
        }}
    ]
}}

請直接返回 JSON，不要加其他文字。"""


@dataclass
class DecomposedTask:
    """A single sub-task decomposed from a complex request."""

    task_id: str
    title: str
    description: str
    role: str
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    tools_needed: List[str] = field(default_factory=list)


@dataclass
class TaskDecomposition:
    """Result of task decomposition."""

    original_task: str
    mode: str  # "parallel" | "sequential" | "pipeline"
    sub_tasks: List[DecomposedTask] = field(default_factory=list)
    reasoning: str = ""


class TaskDecomposer:
    """Decomposes complex tasks into sub-tasks using LLM.

    Args:
        llm_service: LLM service implementing generate() or generate_structured().
        tool_names: List of available tool names for the prompt.
    """

    def __init__(
        self,
        llm_service: Any,
        tool_names: Optional[List[str]] = None,
    ) -> None:
        self._llm = llm_service
        self._tool_names = tool_names or []

    async def decompose(self, task: str) -> TaskDecomposition:
        """Decompose a complex task into sub-tasks.

        Args:
            task: The user's complex request.

        Returns:
            TaskDecomposition with sub-tasks and mode.
        """
        roles_text = ", ".join(get_expert_role_names())
        expert_details = get_expert_descriptions()
        tools_text = ", ".join(self._tool_names) if self._tool_names else "assess_risk, search_knowledge, search_memory, create_task"

        prompt = DECOMPOSE_PROMPT.format(
            roles=roles_text,
            expert_details=expert_details,
            tools=tools_text,
            task=task,
        )

        try:
            # Try structured output first
            if hasattr(self._llm, "generate_structured"):
                schema = {
                    "mode": "string",
                    "reasoning": "string",
                    "sub_tasks": [
                        {
                            "title": "string",
                            "description": "string",
                            "role": "string",
                            "priority": "number",
                            "tools_needed": ["string"],
                        }
                    ],
                }
                result = await self._llm.generate_structured(
                    prompt=prompt,
                    output_schema=schema,
                    max_tokens=2000,
                    temperature=0.3,
                )
            else:
                # Fallback to generate + parse
                raw = await self._llm.generate(
                    prompt=prompt, max_tokens=2000, temperature=0.3,
                )
                result = self._parse_json(raw)

            return self._build_decomposition(task, result)

        except Exception as e:
            logger.warning("TaskDecomposer: LLM decomposition failed: %s, using single-task fallback", e)
            return self._single_task_fallback(task)

    def _build_decomposition(self, original_task: str, result: Dict[str, Any]) -> TaskDecomposition:
        """Build TaskDecomposition from LLM result."""
        sub_tasks: List[DecomposedTask] = []
        valid_roles = set(get_expert_role_names())

        for item in result.get("sub_tasks", []):
            role = item.get("role", "general")
            if role not in valid_roles:
                role = "general"

            sub_tasks.append(DecomposedTask(
                task_id=str(uuid.uuid4())[:8],
                title=item.get("title", "Sub-task"),
                description=item.get("description", ""),
                role=role,
                priority=item.get("priority", 1),
                tools_needed=item.get("tools_needed", []),
            ))

        if not sub_tasks:
            return self._single_task_fallback(original_task)

        return TaskDecomposition(
            original_task=original_task,
            mode=result.get("mode", "parallel"),
            sub_tasks=sub_tasks,
            reasoning=result.get("reasoning", ""),
        )

    def _single_task_fallback(self, task: str) -> TaskDecomposition:
        """Fallback: wrap entire task as a single sub-task."""
        return TaskDecomposition(
            original_task=task,
            mode="parallel",
            sub_tasks=[
                DecomposedTask(
                    task_id=str(uuid.uuid4())[:8],
                    title="Task Analysis",
                    description=task,
                    role="general",
                    priority=1,
                )
            ],
            reasoning="Single task — no decomposition needed",
        )

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        """Extract JSON from LLM text response."""
        text = raw.strip()
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting from markdown code block
        if "```" in text:
            start = text.find("```")
            end = text.rfind("```")
            if start != end:
                inner = text[start:end].split("\n", 1)[-1]
                try:
                    return json.loads(inner)
                except json.JSONDecodeError:
                    pass
        # Try finding first { to last }
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Cannot parse JSON from LLM response: {text[:200]}")
