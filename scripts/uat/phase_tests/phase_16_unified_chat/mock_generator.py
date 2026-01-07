"""
Phase 16: Mock SSE Event Generator

模擬 AG-UI SSE 事件生成器，用於在無後端情況下運行測試。
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class MockSSEGenerator:
    """
    模擬 AG-UI SSE 事件生成器

    支援生成所有 15 種 AG-UI 事件類型，用於測試前端邏輯。
    """

    def __init__(self):
        self.run_id = str(uuid.uuid4())
        self.message_id = str(uuid.uuid4())
        self.thread_id = str(uuid.uuid4())

    def _timestamp(self) -> str:
        """生成 ISO 時間戳"""
        return datetime.now().isoformat()

    # =========================================================================
    # Run Lifecycle Events
    # =========================================================================

    def generate_run_started(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """生成 RUN_STARTED 事件"""
        return {
            "type": "RUN_STARTED",
            "timestamp": self._timestamp(),
            "runId": run_id or self.run_id,
            "threadId": self.thread_id,
        }

    def generate_run_finished(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """生成 RUN_FINISHED 事件"""
        return {
            "type": "RUN_FINISHED",
            "timestamp": self._timestamp(),
            "runId": run_id or self.run_id,
        }

    def generate_run_error(
        self,
        error_message: str,
        error_code: str = "EXECUTION_ERROR",
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成 RUN_ERROR 事件"""
        return {
            "type": "RUN_ERROR",
            "timestamp": self._timestamp(),
            "runId": run_id or self.run_id,
            "error": {
                "code": error_code,
                "message": error_message,
            },
        }

    # =========================================================================
    # Message Events
    # =========================================================================

    def generate_text_message_start(
        self,
        message_id: Optional[str] = None,
        role: str = "assistant",
    ) -> Dict[str, Any]:
        """生成 TEXT_MESSAGE_START 事件"""
        return {
            "type": "TEXT_MESSAGE_START",
            "timestamp": self._timestamp(),
            "messageId": message_id or self.message_id,
            "role": role,
        }

    def generate_text_message_content(
        self,
        content: str,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成 TEXT_MESSAGE_CONTENT 事件"""
        return {
            "type": "TEXT_MESSAGE_CONTENT",
            "timestamp": self._timestamp(),
            "messageId": message_id or self.message_id,
            "content": content,
        }

    def generate_text_message_end(
        self,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成 TEXT_MESSAGE_END 事件"""
        return {
            "type": "TEXT_MESSAGE_END",
            "timestamp": self._timestamp(),
            "messageId": message_id or self.message_id,
        }

    # =========================================================================
    # Tool Call Events
    # =========================================================================

    def generate_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        requires_approval: bool = False,
        risk_level: str = "low",
    ) -> Dict[str, Any]:
        """生成 TOOL_CALL_START 事件"""
        return {
            "type": "TOOL_CALL_START",
            "timestamp": self._timestamp(),
            "toolCallId": tool_call_id,
            "toolName": tool_name,
            "requiresApproval": requires_approval,
            "riskLevel": risk_level,
        }

    def generate_tool_call_args(
        self,
        tool_call_id: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成 TOOL_CALL_ARGS 事件"""
        return {
            "type": "TOOL_CALL_ARGS",
            "timestamp": self._timestamp(),
            "toolCallId": tool_call_id,
            "arguments": arguments,
        }

    def generate_tool_call_end(
        self,
        tool_call_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成 TOOL_CALL_END 事件"""
        event = {
            "type": "TOOL_CALL_END",
            "timestamp": self._timestamp(),
            "toolCallId": tool_call_id,
        }
        if result is not None:
            event["result"] = result
        if error:
            event["error"] = error
        return event

    # =========================================================================
    # State Events
    # =========================================================================

    def generate_state_snapshot(
        self,
        state: Dict[str, Any],
        version: int = 1,
    ) -> Dict[str, Any]:
        """生成 STATE_SNAPSHOT 事件"""
        return {
            "type": "STATE_SNAPSHOT",
            "timestamp": self._timestamp(),
            "snapshot": state,
            "version": version,
            "metadata": {"source": "simulation"},
        }

    def generate_state_delta(
        self,
        delta: List[Dict[str, Any]],
        version: int = 2,
        base_version: int = 1,
    ) -> Dict[str, Any]:
        """生成 STATE_DELTA 事件"""
        return {
            "type": "STATE_DELTA",
            "timestamp": self._timestamp(),
            "delta": delta,
            "version": version,
            "baseVersion": base_version,
        }

    def generate_messages_snapshot(
        self,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """生成 MESSAGES_SNAPSHOT 事件"""
        return {
            "type": "MESSAGES_SNAPSHOT",
            "timestamp": self._timestamp(),
            "messages": messages,
        }

    # =========================================================================
    # Step Events
    # =========================================================================

    def generate_step_started(
        self,
        step_index: int,
        step_name: str,
        total_steps: int,
    ) -> Dict[str, Any]:
        """生成 STEP_STARTED 事件"""
        return {
            "type": "STEP_STARTED",
            "timestamp": self._timestamp(),
            "stepIndex": step_index,
            "stepName": step_name,
            "totalSteps": total_steps,
        }

    def generate_step_finished(
        self,
        step_index: int,
        step_name: str,
        status: str = "completed",
    ) -> Dict[str, Any]:
        """生成 STEP_FINISHED 事件"""
        return {
            "type": "STEP_FINISHED",
            "timestamp": self._timestamp(),
            "stepIndex": step_index,
            "stepName": step_name,
            "status": status,
        }

    # =========================================================================
    # Custom Events
    # =========================================================================

    def generate_custom_event(
        self,
        event_name: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成 CUSTOM 事件"""
        return {
            "type": "CUSTOM",
            "timestamp": self._timestamp(),
            "eventName": event_name,
            "payload": payload,
        }

    def generate_mode_detection(
        self,
        detected_mode: str,
        confidence: float,
        reason: str,
    ) -> Dict[str, Any]:
        """生成模式檢測自定義事件"""
        return self.generate_custom_event(
            event_name="MODE_DETECTION",
            payload={
                "mode": detected_mode,
                "confidence": confidence,
                "reason": reason,
            },
        )

    def generate_token_update(
        self,
        tokens_used: int,
        tokens_limit: int,
    ) -> Dict[str, Any]:
        """生成 Token 使用量更新事件"""
        return self.generate_custom_event(
            event_name="TOKEN_UPDATE",
            payload={
                "tokensUsed": tokens_used,
                "tokensLimit": tokens_limit,
            },
        )

    # =========================================================================
    # Composite Event Sequences
    # =========================================================================

    def generate_message_stream(
        self,
        content: str,
        chunk_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        生成完整的消息流式事件序列

        Args:
            content: 消息內容
            chunk_size: 每個 chunk 的字符數

        Returns:
            事件列表
        """
        events = []
        message_id = str(uuid.uuid4())

        # RUN_STARTED
        events.append(self.generate_run_started())

        # TEXT_MESSAGE_START
        events.append(self.generate_text_message_start(message_id))

        # TEXT_MESSAGE_CONTENT (chunks)
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            events.append(self.generate_text_message_content(chunk, message_id))

        # TEXT_MESSAGE_END
        events.append(self.generate_text_message_end(message_id))

        # RUN_FINISHED
        events.append(self.generate_run_finished())

        return events

    def generate_tool_call_sequence(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        requires_approval: bool = False,
        risk_level: str = "low",
    ) -> List[Dict[str, Any]]:
        """
        生成完整的工具呼叫事件序列

        Args:
            tool_name: 工具名稱
            arguments: 工具參數
            result: 工具執行結果
            requires_approval: 是否需要審批
            risk_level: 風險等級

        Returns:
            事件列表
        """
        events = []
        tool_call_id = str(uuid.uuid4())

        events.append(
            self.generate_tool_call_start(
                tool_call_id, tool_name, requires_approval, risk_level
            )
        )
        events.append(self.generate_tool_call_args(tool_call_id, arguments))
        events.append(self.generate_tool_call_end(tool_call_id, result))

        return events

    def generate_workflow_sequence(
        self,
        steps: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        生成工作流步驟事件序列

        Args:
            steps: 步驟列表，每個步驟包含 name 和 status

        Returns:
            事件列表
        """
        events = []
        total_steps = len(steps)

        for i, step in enumerate(steps):
            events.append(
                self.generate_step_started(i, step.get("name", f"Step {i+1}"), total_steps)
            )
            events.append(
                self.generate_step_finished(
                    i, step.get("name", f"Step {i+1}"), step.get("status", "completed")
                )
            )

        return events

    def generate_intent_analysis_response(
        self,
        input_text: str,
    ) -> Dict[str, Any]:
        """
        生成模擬的意圖分析回應

        根據輸入文本簡單判斷模式
        """
        # 簡單的關鍵字匹配
        workflow_keywords = [
            "process",
            "invoice",
            "approve",
            "workflow",
            "submit",
            "execute",
            "run",
            "create report",
            "generate",
            "calculate",
        ]
        chat_keywords = [
            "what",
            "how",
            "why",
            "explain",
            "tell me",
            "help",
            "question",
            "?",
        ]

        input_lower = input_text.lower()

        workflow_score = sum(
            1 for kw in workflow_keywords if kw in input_lower
        )
        chat_score = sum(1 for kw in chat_keywords if kw in input_lower)

        if workflow_score > chat_score:
            mode = "WORKFLOW_MODE"
            confidence = min(0.6 + workflow_score * 0.1, 0.95)
            reason = f"Detected {workflow_score} workflow indicators"
        else:
            mode = "CHAT_MODE"
            confidence = min(0.6 + chat_score * 0.1, 0.95)
            reason = f"Detected {chat_score} chat indicators"

        return {
            "mode": mode,
            "confidence": confidence,
            "reason": reason,
            "input_text": input_text,
            "analysis": {
                "workflow_score": workflow_score,
                "chat_score": chat_score,
            },
        }
