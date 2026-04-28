"""
Session Agent Bridge - Sprint 46 S46-1

建立 Session 與 Agent 的橋接層，提供:
- 統一訊息處理介面
- 串流執行支援
- 工具審批整合
- 錯誤處理

依賴:
- SessionService (Phase 10)
- AgentExecutor (S45-1)
- ToolCallHandler (S45-3)
- ToolApprovalManager (S46-4)
- ExecutionEvent (S45-4)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
)
import logging
import uuid

from src.domain.sessions.models import (
    Session,
    SessionStatus,
    Message,
    MessageRole,
    Attachment,
    ToolCall,
    ToolCallStatus,
)
from src.domain.sessions.events import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionEventFactory,
    ToolCallInfo,
)
from src.domain.sessions.executor import (
    AgentExecutor,
    AgentConfig,
    ExecutionConfig,
    ChatMessage,
)
from src.domain.sessions.tool_handler import (
    ToolCallHandler,
    ParsedToolCall,
    ToolExecutionResult,
)
from src.domain.sessions.approval import (
    ToolApprovalManager,
    ToolApprovalRequest,
    ApprovalStatus,
    ApprovalNotFoundError,
    ApprovalAlreadyResolvedError,
    ApprovalExpiredError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols
# =============================================================================


class SessionServiceProtocol(Protocol):
    """SessionService 協議

    定義 SessionService 需要實現的介面。
    """

    async def get_session(
        self,
        session_id: str,
        include_messages: bool = True,
    ) -> Optional[Session]:
        """獲取 Session"""
        ...

    async def send_message(
        self,
        session_id: str,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """發送用戶訊息"""
        ...

    async def add_assistant_message(
        self,
        session_id: str,
        content: str,
        tool_calls: Optional[List[ToolCall]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """添加助手回覆"""
        ...

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> List[Message]:
        """獲取訊息歷史"""
        ...

    async def get_conversation_for_llm(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """獲取 LLM 格式的對話歷史"""
        ...


class AgentRepositoryProtocol(Protocol):
    """AgentRepository 協議

    定義 AgentRepository 需要實現的介面。
    """

    async def get(self, agent_id: str) -> Optional[Any]:
        """獲取 Agent"""
        ...


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class BridgeConfig:
    """Bridge 配置

    Attributes:
        max_tool_iterations: 最大工具迭代次數
        stream_by_default: 預設是否串流
        save_tool_results: 是否保存工具結果到訊息
        approval_timeout: 審批超時時間（秒）
        enable_approval: 是否啟用審批流程
    """
    max_tool_iterations: int = 10
    stream_by_default: bool = True
    save_tool_results: bool = True
    approval_timeout: int = 300
    enable_approval: bool = True


@dataclass
class ProcessingContext:
    """處理上下文

    追蹤單次訊息處理的狀態。
    """
    session_id: str
    execution_id: str
    iteration: int = 0
    content_parts: List[str] = field(default_factory=list)
    tool_calls: List[ParsedToolCall] = field(default_factory=list)
    tool_results: List[ToolExecutionResult] = field(default_factory=list)
    pending_approvals: List[str] = field(default_factory=list)
    completed: bool = False
    error: Optional[str] = None


# =============================================================================
# Errors
# =============================================================================


class BridgeError(Exception):
    """Bridge 錯誤基類"""
    pass


class SessionNotFoundError(BridgeError):
    """Session 未找到錯誤"""
    pass


class SessionNotActiveError(BridgeError):
    """Session 非活躍狀態錯誤"""
    pass


class AgentNotFoundError(BridgeError):
    """Agent 未找到錯誤"""
    pass


class MaxIterationsExceededError(BridgeError):
    """超過最大迭代次數錯誤"""
    pass


class PendingApprovalError(BridgeError):
    """存在待處理審批錯誤"""
    pass


# =============================================================================
# Session Agent Bridge
# =============================================================================


class SessionAgentBridge:
    """Session Agent 橋接器

    連接 Session 和 Agent 執行層，提供:
    - 統一的訊息處理介面
    - 串流與非串流模式支援
    - 工具調用與審批整合
    - 多輪對話管理

    Example:
        ```python
        bridge = SessionAgentBridge(
            session_service=session_service,
            agent_executor=agent_executor,
            agent_repository=agent_repository,
            approval_manager=approval_manager,
        )

        # 處理訊息（串流模式）
        async for event in bridge.process_message(
            session_id="session-123",
            content="Hello, how can you help me?",
        ):
            print(event.to_json())

        # 處理工具審批
        await bridge.handle_tool_approval(
            session_id="session-123",
            approval_id="approval-456",
            approved=True,
            feedback="Approved by user",
        )
        ```
    """

    def __init__(
        self,
        session_service: SessionServiceProtocol,
        agent_executor: AgentExecutor,
        agent_repository: AgentRepositoryProtocol,
        tool_handler: Optional[ToolCallHandler] = None,
        approval_manager: Optional[ToolApprovalManager] = None,
        config: Optional[BridgeConfig] = None,
    ):
        """初始化橋接器

        Args:
            session_service: Session 服務
            agent_executor: Agent 執行器
            agent_repository: Agent 存儲
            tool_handler: 工具處理器
            approval_manager: 審批管理器
            config: Bridge 配置
        """
        self._session_service = session_service
        self._agent_executor = agent_executor
        self._agent_repository = agent_repository
        self._tool_handler = tool_handler
        self._approval_manager = approval_manager
        self._config = config or BridgeConfig()

        # 追蹤活躍的處理上下文
        self._active_contexts: Dict[str, ProcessingContext] = {}

        logger.info(
            f"SessionAgentBridge initialized: "
            f"approval={approval_manager is not None}, "
            f"tool_handler={tool_handler is not None}"
        )

    # =========================================================================
    # Main API
    # =========================================================================

    async def process_message(
        self,
        session_id: str,
        content: str,
        attachments: Optional[List[Attachment]] = None,
        stream: Optional[bool] = None,
        execution_config: Optional[ExecutionConfig] = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """處理用戶訊息

        主要入口點，處理用戶訊息並返回執行事件流。

        Args:
            session_id: Session ID
            content: 訊息內容
            attachments: 附件列表
            stream: 是否串流（None 使用預設）
            execution_config: 執行配置

        Yields:
            ExecutionEvent: 執行事件

        Raises:
            SessionNotFoundError: Session 未找到
            SessionNotActiveError: Session 非活躍
            AgentNotFoundError: Agent 未找到
        """
        execution_id = str(uuid.uuid4())
        stream = stream if stream is not None else self._config.stream_by_default

        logger.info(
            f"Processing message for session {session_id}, "
            f"execution_id={execution_id}, stream={stream}"
        )

        try:
            # 1. 驗證並獲取 Session
            session = await self._get_active_session(session_id)

            # 2. 獲取 Agent 配置
            agent_config = await self._get_agent_config(session.agent_id)

            # 3. 保存用戶訊息
            await self._session_service.send_message(
                session_id=session_id,
                content=content,
                attachments=attachments,
            )

            # 4. 創建處理上下文
            context = ProcessingContext(
                session_id=session_id,
                execution_id=execution_id,
            )
            self._active_contexts[execution_id] = context

            # 5. 獲取對話歷史
            messages = await self._session_service.get_conversation_for_llm(session_id)

            # 6. 配置執行參數
            exec_config = execution_config or ExecutionConfig(stream=stream)
            exec_config.stream = stream

            # 7. 執行並處理結果
            async for event in self._execute_with_tools(
                agent_config=agent_config,
                messages=messages,
                context=context,
                exec_config=exec_config,
            ):
                yield event

            # 8. 保存助手回覆
            if context.content_parts:
                full_content = "".join(context.content_parts)
                await self._session_service.add_assistant_message(
                    session_id=session_id,
                    content=full_content,
                    metadata={
                        "execution_id": execution_id,
                        "tool_calls_count": len(context.tool_results),
                    },
                )

        except BridgeError:
            raise
        except Exception as e:
            logger.error(
                f"Error processing message for session {session_id}: {e}",
                exc_info=True,
            )
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=str(e),
                error_code="BRIDGE_ERROR",
            )
        finally:
            # 清理上下文
            self._active_contexts.pop(execution_id, None)

    async def handle_tool_approval(
        self,
        session_id: str,
        approval_id: str,
        approved: bool,
        feedback: Optional[str] = None,
        approver_id: Optional[str] = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """處理工具審批

        處理用戶對工具調用的審批決定。

        Args:
            session_id: Session ID
            approval_id: 審批請求 ID
            approved: 是否批准
            feedback: 審批反饋
            approver_id: 審批者 ID

        Yields:
            ExecutionEvent: 執行事件

        Raises:
            ApprovalNotFoundError: 審批請求未找到
            ApprovalAlreadyResolvedError: 審批已處理
            ApprovalExpiredError: 審批已過期
        """
        if not self._approval_manager:
            logger.warning("Approval manager not configured")
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id="",
                error_message="Approval manager not configured",
                error_code="APPROVAL_NOT_CONFIGURED",
            )
            return

        logger.info(
            f"Handling tool approval: approval_id={approval_id}, "
            f"approved={approved}, approver={approver_id}"
        )

        try:
            # 1. 解決審批請求
            approval = await self._approval_manager.resolve_approval(
                approval_id=approval_id,
                approved=approved,
                resolved_by=approver_id,
                feedback=feedback,
            )

            # 2. 發送審批回應事件
            yield ExecutionEventFactory.approval_response(
                session_id=session_id,
                execution_id=approval.execution_id,
                approval_request_id=approval_id,
                approved=approved,
                feedback=feedback,
            )

            # 3. 如果批准，執行工具並繼續處理
            if approved:
                async for event in self._continue_after_approval(
                    session_id=session_id,
                    approval=approval,
                ):
                    yield event

        except (ApprovalNotFoundError, ApprovalAlreadyResolvedError, ApprovalExpiredError) as e:
            logger.error(f"Approval error: {e}")
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id="",
                error_message=str(e),
                error_code=type(e).__name__.upper(),
            )

    async def get_pending_approvals(
        self,
        session_id: str,
    ) -> List[ToolApprovalRequest]:
        """獲取待處理的審批請求

        Args:
            session_id: Session ID

        Returns:
            待處理的審批請求列表
        """
        if not self._approval_manager:
            return []

        return await self._approval_manager.get_pending_approvals(session_id)

    async def cancel_pending_approvals(
        self,
        session_id: str,
        reason: str = "Cancelled by user",
    ) -> int:
        """取消所有待處理的審批

        Args:
            session_id: Session ID
            reason: 取消原因

        Returns:
            取消的審批數量
        """
        if not self._approval_manager:
            return 0

        pending = await self._approval_manager.get_pending_approvals(session_id)
        cancelled = 0

        for approval in pending:
            try:
                await self._approval_manager.cancel_approval(
                    approval_id=approval.id,
                    cancelled_by="system",
                    reason=reason,
                )
                cancelled += 1
            except Exception as e:
                logger.warning(f"Failed to cancel approval {approval.id}: {e}")

        return cancelled

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _get_active_session(self, session_id: str) -> Session:
        """獲取活躍的 Session

        Args:
            session_id: Session ID

        Returns:
            Session

        Raises:
            SessionNotFoundError: Session 未找到
            SessionNotActiveError: Session 非活躍
        """
        session = await self._session_service.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")

        if session.status != SessionStatus.ACTIVE:
            raise SessionNotActiveError(
                f"Session is not active: {session.status.value}"
            )

        return session

    async def _get_agent_config(self, agent_id: str) -> AgentConfig:
        """獲取 Agent 配置

        Args:
            agent_id: Agent ID

        Returns:
            AgentConfig

        Raises:
            AgentNotFoundError: Agent 未找到
        """
        agent = await self._agent_repository.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")

        return AgentConfig.from_agent(agent)

    async def _execute_with_tools(
        self,
        agent_config: AgentConfig,
        messages: List[Dict[str, Any]],
        context: ProcessingContext,
        exec_config: ExecutionConfig,
    ) -> AsyncIterator[ExecutionEvent]:
        """執行 Agent 並處理工具調用

        支援多輪工具調用。

        Args:
            agent_config: Agent 配置
            messages: 對話歷史
            context: 處理上下文
            exec_config: 執行配置

        Yields:
            ExecutionEvent: 執行事件
        """
        current_messages = list(messages)

        while context.iteration < self._config.max_tool_iterations:
            context.iteration += 1

            logger.debug(
                f"Execution iteration {context.iteration} for {context.execution_id}"
            )

            # 執行 Agent
            has_tool_calls = False
            async for event in self._agent_executor.execute(
                agent_config=agent_config,
                messages=current_messages,
                session_id=context.session_id,
                execution_config=exec_config,
            ):
                yield event

                # 收集內容
                if event.event_type == ExecutionEventType.CONTENT_DELTA:
                    context.content_parts.append(event.content or "")
                elif event.event_type == ExecutionEventType.CONTENT:
                    context.content_parts.append(event.content or "")

                # 檢測工具調用
                elif event.event_type == ExecutionEventType.TOOL_CALL:
                    has_tool_calls = True
                    if event.tool_call:
                        parsed = ParsedToolCall(
                            id=event.tool_call.id,
                            name=event.tool_call.name,
                            arguments=event.tool_call.arguments,
                        )
                        context.tool_calls.append(parsed)

                # 檢測完成
                elif event.event_type == ExecutionEventType.DONE:
                    if event.finish_reason == "tool_calls":
                        has_tool_calls = True
                    else:
                        context.completed = True

                # 檢測錯誤
                elif event.event_type == ExecutionEventType.ERROR:
                    context.error = event.error
                    context.completed = True

            # 如果沒有工具調用或已完成，結束循環
            if not has_tool_calls or context.completed:
                break

            # 處理工具調用
            if context.tool_calls and self._tool_handler:
                tool_results = []

                for tool_call in context.tool_calls:
                    # 檢查是否需要審批
                    requires_approval = self._requires_approval(tool_call)

                    if requires_approval and self._approval_manager:
                        # 創建審批請求
                        approval = await self._approval_manager.create_approval_request(
                            session_id=context.session_id,
                            execution_id=context.execution_id,
                            tool_call={
                                "id": tool_call.id,
                                "name": tool_call.name,
                                "arguments": tool_call.arguments,
                            },
                            timeout=self._config.approval_timeout,
                        )

                        context.pending_approvals.append(approval.id)

                        # 發送審批請求事件
                        yield ExecutionEventFactory.approval_required(
                            session_id=context.session_id,
                            execution_id=context.execution_id,
                            approval_request_id=approval.id,
                            tool_call_id=tool_call.id,
                            tool_name=tool_call.name,
                            arguments=tool_call.arguments,
                        )

                        # 暫停執行，等待審批
                        logger.info(
                            f"Waiting for approval: {approval.id} "
                            f"for tool {tool_call.name}"
                        )
                        return  # 結束執行，等待審批回調

                    else:
                        # 直接執行工具
                        result = await self._tool_handler.execute_tool(
                            tool_call=tool_call,
                            session_id=context.session_id,
                            execution_id=context.execution_id,
                        )
                        tool_results.append(result)
                        context.tool_results.append(result)

                        # 發送工具結果事件
                        yield ExecutionEventFactory.tool_result(
                            session_id=context.session_id,
                            execution_id=context.execution_id,
                            tool_call_id=result.tool_call_id,
                            tool_name=result.name,
                            result=result.result,
                            success=result.success,
                            error_message=result.error,
                        )

                # 清空當前輪次的工具調用
                context.tool_calls.clear()

                # 將工具結果添加到訊息
                if tool_results:
                    tool_messages = self._tool_handler.results_to_messages(tool_results)
                    current_messages.extend(tool_messages)

        if context.iteration >= self._config.max_tool_iterations:
            logger.warning(
                f"Max iterations reached for execution {context.execution_id}"
            )
            yield ExecutionEventFactory.error(
                session_id=context.session_id,
                execution_id=context.execution_id,
                error_message=f"Maximum tool iterations ({self._config.max_tool_iterations}) exceeded",
                error_code="MAX_ITERATIONS_EXCEEDED",
            )

    async def _continue_after_approval(
        self,
        session_id: str,
        approval: ToolApprovalRequest,
    ) -> AsyncIterator[ExecutionEvent]:
        """審批後繼續執行

        Args:
            session_id: Session ID
            approval: 審批請求

        Yields:
            ExecutionEvent: 執行事件
        """
        if not self._tool_handler:
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=approval.execution_id,
                error_message="Tool handler not configured",
                error_code="TOOL_HANDLER_NOT_CONFIGURED",
            )
            return

        # 執行被批准的工具
        tool_call = ParsedToolCall(
            id=approval.tool_call.get("id", str(uuid.uuid4())),
            name=approval.tool_call.get("name", ""),
            arguments=approval.tool_call.get("arguments", {}),
        )

        result = await self._tool_handler.execute_tool(
            tool_call=tool_call,
            session_id=session_id,
            execution_id=approval.execution_id,
        )

        # 發送工具結果事件
        yield ExecutionEventFactory.tool_result(
            session_id=session_id,
            execution_id=approval.execution_id,
            tool_call_id=result.tool_call_id,
            tool_name=result.name,
            result=result.result,
            success=result.success,
            error_message=result.error,
        )

        # 繼續對話（如果需要）
        try:
            session = await self._get_active_session(session_id)
            agent_config = await self._get_agent_config(session.agent_id)

            # 獲取更新的對話歷史
            messages = await self._session_service.get_conversation_for_llm(session_id)

            # 添加工具結果
            messages.append(result.to_llm_message())

            # 創建新的處理上下文
            context = ProcessingContext(
                session_id=session_id,
                execution_id=approval.execution_id,
            )

            # 繼續執行
            async for event in self._execute_with_tools(
                agent_config=agent_config,
                messages=messages,
                context=context,
                exec_config=ExecutionConfig(stream=self._config.stream_by_default),
            ):
                yield event

            # 保存助手回覆
            if context.content_parts:
                full_content = "".join(context.content_parts)
                await self._session_service.add_assistant_message(
                    session_id=session_id,
                    content=full_content,
                    metadata={
                        "execution_id": approval.execution_id,
                        "continued_from_approval": approval.id,
                    },
                )

        except Exception as e:
            logger.error(f"Error continuing after approval: {e}", exc_info=True)
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=approval.execution_id,
                error_message=str(e),
                error_code="CONTINUE_ERROR",
            )

    def _requires_approval(self, tool_call: ParsedToolCall) -> bool:
        """檢查工具調用是否需要審批

        Args:
            tool_call: 工具調用

        Returns:
            是否需要審批
        """
        if not self._config.enable_approval:
            return False

        if not self._tool_handler:
            return False

        # 檢查工具處理器的配置
        if hasattr(self._tool_handler, 'config'):
            config = self._tool_handler.config
            if tool_call.name in config.require_approval_tools:
                return True

        return False


# =============================================================================
# Factory Functions
# =============================================================================


def create_session_agent_bridge(
    session_service: SessionServiceProtocol,
    agent_executor: AgentExecutor,
    agent_repository: AgentRepositoryProtocol,
    tool_handler: Optional[ToolCallHandler] = None,
    approval_manager: Optional[ToolApprovalManager] = None,
    config: Optional[BridgeConfig] = None,
) -> SessionAgentBridge:
    """創建 SessionAgentBridge 實例

    Factory 函數，便於依賴注入。

    Args:
        session_service: Session 服務
        agent_executor: Agent 執行器
        agent_repository: Agent 存儲
        tool_handler: 工具處理器
        approval_manager: 審批管理器
        config: Bridge 配置

    Returns:
        SessionAgentBridge 實例
    """
    return SessionAgentBridge(
        session_service=session_service,
        agent_executor=agent_executor,
        agent_repository=agent_repository,
        tool_handler=tool_handler,
        approval_manager=approval_manager,
        config=config,
    )
