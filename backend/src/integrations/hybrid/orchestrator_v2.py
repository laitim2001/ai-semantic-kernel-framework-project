# =============================================================================
# IPA Platform - Hybrid Orchestrator V2
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor (S54-3)
# Sprint 98: Phase 28 Integration - FrameworkSelector + Phase 28 Components
#
# 重構後的混合編排器，整合 Phase 13 所有核心組件:
#   - FrameworkSelector (IntentRouter): 框架選擇和執行模式選擇
#   - ContextBridge: 跨框架上下文同步
#   - UnifiedToolExecutor: 統一 Tool 執行層
#   - MAFToolCallback: MAF Tool 回調整合
#
# Phase 28 新增組件:
#   - InputGateway: 來源識別和分流處理
#   - BusinessIntentRouter: IT 意圖分類
#   - GuidedDialogEngine: 引導式對話
#   - RiskAssessor: 風險評估
#   - HITLController: 審批流程控制
#
# 執行模式:
#   - WORKFLOW_MODE: 多步驟結構化工作流程 (MAF 主導)
#   - CHAT_MODE: 對話式交互 (Claude 主導)
#   - HYBRID_MODE: 動態切換模式
#
# Dependencies:
#   - FrameworkSelector (src.integrations.hybrid.intent)
#   - ContextBridge (src.integrations.hybrid.context)
#   - UnifiedToolExecutor (src.integrations.hybrid.execution)
#   - Phase 28 Components (src.integrations.orchestration)
# =============================================================================

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from src.integrations.hybrid.intent import (
    ExecutionMode,
    FrameworkSelector,
    IntentAnalysis,
    IntentRouter,
    SessionContext,
)
from src.integrations.hybrid.context import (
    ContextBridge,
    HybridContext,
    MAFContext,
    ClaudeContext,
    SyncResult,
)
from src.integrations.hybrid.execution import (
    UnifiedToolExecutor,
    ToolSource,
    ToolExecutionResult,
    MAFToolCallback,
    create_maf_callback,
)

# Phase 28 Components (Sprint 93-97)
from src.integrations.orchestration import (
    # Sprint 93: BusinessIntentRouter
    BusinessIntentRouter,
    RoutingDecision,
    CompletenessInfo,
    # Sprint 94: GuidedDialogEngine
    GuidedDialogEngine,
    DialogResponse,
    # Sprint 95: InputGateway
    InputGateway,
    IncomingRequest,
    SourceType,
    # Sprint 96: RiskAssessor
    RiskAssessor,
    RiskAssessment,
    # Sprint 97: HITLController
    HITLController,
    ApprovalRequest,
    ApprovalStatus,
)

if TYPE_CHECKING:
    from src.integrations.claude_sdk.hybrid.selector import FrameworkSelector

logger = logging.getLogger(__name__)


class OrchestratorMode(str, Enum):
    """Orchestrator operation mode."""

    V1_COMPAT = "v1_compat"  # V1 兼容模式
    V2_FULL = "v2_full"  # V2 完整功能
    V2_MINIMAL = "v2_minimal"  # V2 最小功能 (無 Intent Router)


@dataclass
class OrchestratorConfig:
    """Configuration for HybridOrchestratorV2."""

    mode: OrchestratorMode = OrchestratorMode.V2_FULL
    primary_framework: str = "claude_sdk"
    auto_switch: bool = True
    switch_confidence_threshold: float = 0.7
    timeout: float = 300.0
    max_retries: int = 3
    enable_metrics: bool = True
    enable_tool_callback: bool = True


@dataclass
class ExecutionContextV2:
    """Enhanced execution context for V2."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hybrid_context: Optional[HybridContext] = None
    intent_analysis: Optional[IntentAnalysis] = None
    current_mode: ExecutionMode = ExecutionMode.CHAT_MODE
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    tool_executions: List[ToolExecutionResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)


@dataclass
class HybridResultV2:
    """Enhanced result from V2 orchestrator."""

    success: bool
    content: str = ""
    error: Optional[str] = None
    framework_used: str = ""
    execution_mode: ExecutionMode = ExecutionMode.CHAT_MODE
    session_id: Optional[str] = None
    intent_analysis: Optional[IntentAnalysis] = None
    tool_results: List[ToolExecutionResult] = field(default_factory=list)
    sync_result: Optional[SyncResult] = None
    duration: float = 0.0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class HybridOrchestratorV2:
    """
    重構後的混合編排器 V2。

    整合 Phase 13 所有核心組件，提供智能的執行模式選擇、
    跨框架上下文同步和統一的 Tool 執行。

    Key Features (Phase 13):
    - 智能框架選擇和模式選擇 (FrameworkSelector)
    - 跨框架上下文同步 (ContextBridge)
    - 統一 Tool 執行層 (UnifiedToolExecutor)
    - MAF Tool 回調整合 (MAFToolCallback)
    - 向後兼容 V1 API

    Phase 28 Features (Sprint 98 Integration):
    - InputGateway: 來源識別和分流處理
    - BusinessIntentRouter: IT 意圖分類
    - GuidedDialogEngine: 引導式對話
    - RiskAssessor: 風險評估
    - HITLController: 審批流程控制

    Execute Flow (Phase 28):
    1. InputGateway → 來源識別和處理
    2. 檢查 completeness.is_sufficient
    3. GuidedDialogEngine → 資訊收集 (如需要)
    4. RiskAssessor → 風險評估
    5. HITLController → 審批 (如需要)
    6. FrameworkSelector → 框架選擇
    7. 執行 (Claude SDK / MAF)
    """

    def __init__(
        self,
        *,
        config: Optional[OrchestratorConfig] = None,
        # Phase 28 Components (Sprint 93-97)
        input_gateway: Optional[InputGateway] = None,
        business_router: Optional[BusinessIntentRouter] = None,
        guided_dialog: Optional[GuidedDialogEngine] = None,
        risk_assessor: Optional[RiskAssessor] = None,
        hitl_controller: Optional[HITLController] = None,
        # Phase 13 Components (Sprint 52-54)
        framework_selector: Optional[FrameworkSelector] = None,
        context_bridge: Optional[ContextBridge] = None,
        unified_executor: Optional[UnifiedToolExecutor] = None,
        maf_callback: Optional[MAFToolCallback] = None,
        claude_executor: Optional[Callable] = None,
        maf_executor: Optional[Callable] = None,
        # Backward compatibility aliases
        intent_router: Optional[FrameworkSelector] = None,
    ):
        """
        Initialize HybridOrchestratorV2.

        Args:
            config: Orchestrator configuration

            # Phase 28 Components (Sprint 98 Integration)
            input_gateway: Gateway for source routing (Sprint 95)
            business_router: Business intent router for IT classification (Sprint 93)
            guided_dialog: Guided dialog engine for information gathering (Sprint 94)
            risk_assessor: Risk assessor for operation risk evaluation (Sprint 96)
            hitl_controller: HITL controller for approval workflow (Sprint 97)

            # Phase 13 Components
            framework_selector: Framework selector for mode selection (Sprint 98)
            context_bridge: Bridge for context sync (Sprint 53)
            unified_executor: Unified tool executor (Sprint 54)
            maf_callback: MAF tool callback (Sprint 54)
            claude_executor: Executor for Claude SDK
            maf_executor: Executor for MAF

            # Backward Compatibility
            intent_router: Deprecated - use framework_selector instead
        """
        self._config = config or OrchestratorConfig()

        # Phase 28 Components (Sprint 93-97)
        self._input_gateway = input_gateway
        self._business_router = business_router
        self._guided_dialog = guided_dialog
        self._risk_assessor = risk_assessor
        self._hitl_controller = hitl_controller

        # Phase 13 + Sprint 98 components
        # Support both framework_selector and intent_router (backward compat)
        self._framework_selector = framework_selector or intent_router or FrameworkSelector()
        self._context_bridge = context_bridge or ContextBridge()
        self._unified_executor = unified_executor
        self._maf_callback = maf_callback

        # Executors
        self._claude_executor = claude_executor
        self._maf_executor = maf_executor

        # Session state
        self._sessions: Dict[str, ExecutionContextV2] = {}
        self._active_session: Optional[str] = None

        # Metrics
        self._metrics = OrchestratorMetrics()

        logger.info(
            f"HybridOrchestratorV2 initialized: mode={self._config.mode.value}, "
            f"framework_selector={self._framework_selector is not None}, "
            f"context_bridge={context_bridge is not None}, "
            f"unified_executor={unified_executor is not None}, "
            f"phase_28=[input_gateway={input_gateway is not None}, "
            f"business_router={business_router is not None}, "
            f"guided_dialog={guided_dialog is not None}, "
            f"risk_assessor={risk_assessor is not None}, "
            f"hitl_controller={hitl_controller is not None}]"
        )

    @property
    def config(self) -> OrchestratorConfig:
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

    @property
    def framework_selector(self) -> FrameworkSelector:
        """Get framework selector instance."""
        return self._framework_selector

    @property
    def intent_router(self) -> FrameworkSelector:
        """Get intent router instance (backward compat alias for framework_selector)."""
        return self._framework_selector

    # =========================================================================
    # Phase 28 Component Properties (Sprint 98)
    # =========================================================================

    @property
    def input_gateway(self) -> Optional[InputGateway]:
        """Get input gateway instance (Phase 28, Sprint 95)."""
        return self._input_gateway

    @property
    def business_router(self) -> Optional[BusinessIntentRouter]:
        """Get business intent router instance (Phase 28, Sprint 93)."""
        return self._business_router

    @property
    def guided_dialog(self) -> Optional[GuidedDialogEngine]:
        """Get guided dialog engine instance (Phase 28, Sprint 94)."""
        return self._guided_dialog

    @property
    def risk_assessor(self) -> Optional[RiskAssessor]:
        """Get risk assessor instance (Phase 28, Sprint 96)."""
        return self._risk_assessor

    @property
    def hitl_controller(self) -> Optional[HITLController]:
        """Get HITL controller instance (Phase 28, Sprint 97)."""
        return self._hitl_controller

    def has_phase_28_components(self) -> bool:
        """Check if Phase 28 components are configured."""
        return any([
            self._input_gateway is not None,
            self._business_router is not None,
            self._guided_dialog is not None,
            self._risk_assessor is not None,
            self._hitl_controller is not None,
        ])

    # =========================================================================
    # Phase 13 Component Properties
    # =========================================================================

    @property
    def context_bridge(self) -> ContextBridge:
        """Get context bridge instance."""
        return self._context_bridge

    @property
    def unified_executor(self) -> Optional[UnifiedToolExecutor]:
        """Get unified executor instance."""
        return self._unified_executor

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new execution session.

        Args:
            session_id: Optional custom session ID
            metadata: Optional session metadata

        Returns:
            The session ID
        """
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = ExecutionContextV2(
            session_id=sid,
            metadata=metadata or {},
        )
        self._active_session = sid
        logger.info(f"Created V2 session: {sid}")
        return sid

    def get_session(self, session_id: str) -> Optional[ExecutionContextV2]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        """Close and remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session == session_id:
                self._active_session = None
            logger.info(f"Closed V2 session: {session_id}")
            return True
        return False

    async def execute(
        self,
        prompt: str,
        *,
        session_id: Optional[str] = None,
        force_mode: Optional[ExecutionMode] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HybridResultV2:
        """
        Execute a task using intelligent mode selection.

        Args:
            prompt: The task prompt or user message
            session_id: Optional session ID (creates new if not provided)
            force_mode: Force specific execution mode
            tools: Available tools for execution
            max_tokens: Maximum tokens for response
            timeout: Execution timeout in seconds
            metadata: Additional metadata for execution

        Returns:
            HybridResultV2 with execution outcome
        """
        start_time = time.time()

        # Get or create session
        if session_id and session_id in self._sessions:
            context = self._sessions[session_id]
        else:
            sid = self.create_session(session_id, metadata)
            context = self._sessions[sid]

        context.last_activity = time.time()

        # S75-5: Store execution metadata in context (including multimodal_content)
        if metadata:
            context.metadata.update(metadata)

        try:
            # 1. Intent Analysis (skip if forcing mode or in minimal mode)
            if force_mode:
                intent_analysis = IntentAnalysis(
                    mode=force_mode,
                    confidence=1.0,
                    reasoning="Forced mode by user request",
                    analysis_time_ms=0.0,  # No analysis needed for forced mode
                )
            elif self._config.mode == OrchestratorMode.V2_MINIMAL:
                intent_analysis = IntentAnalysis(
                    mode=ExecutionMode.CHAT_MODE,
                    confidence=0.8,
                    reasoning="Minimal mode - defaulting to CHAT",
                    analysis_time_ms=0.0,  # No analysis in minimal mode
                )
            else:
                # Build session context for analysis
                # Set workflow_active=True if we're currently in workflow mode
                # This enables context boost for follow-up messages in workflows
                is_workflow_active = context.current_mode == ExecutionMode.WORKFLOW_MODE
                # pending_steps > 0 enables the context boost in RuleBasedClassifier
                pending_steps = 1 if is_workflow_active else 0

                session_context = SessionContext(
                    session_id=context.session_id,
                    conversation_history=context.conversation_history,
                    current_mode=context.current_mode,
                    workflow_active=is_workflow_active,
                    pending_steps=pending_steps,
                )
                intent_analysis = await self._framework_selector.analyze_intent(
                    user_input=prompt,
                    session_context=session_context,
                )

            context.intent_analysis = intent_analysis
            context.current_mode = intent_analysis.mode

            # 2. Prepare Hybrid Context
            hybrid_context = await self._prepare_hybrid_context(context, prompt)
            context.hybrid_context = hybrid_context

            # 3. Execute based on mode
            if intent_analysis.mode == ExecutionMode.WORKFLOW_MODE:
                result = await self._execute_workflow_mode(
                    prompt, context, intent_analysis, tools, max_tokens, timeout
                )
            elif intent_analysis.mode == ExecutionMode.CHAT_MODE:
                result = await self._execute_chat_mode(
                    prompt, context, intent_analysis, tools, max_tokens, timeout
                )
            else:  # HYBRID_MODE
                result = await self._execute_hybrid_mode(
                    prompt, context, intent_analysis, tools, max_tokens, timeout
                )

            # 4. Set session_id BEFORE sync to ensure cache update works
            result.session_id = context.session_id

            # 5. Sync context after execution
            if hybrid_context:
                sync_result = await self._context_bridge.sync_after_execution(
                    result, hybrid_context
                )
                result.sync_result = sync_result

            # 6. Update conversation history
            context.conversation_history.append({
                "role": "user",
                "content": prompt,
                "timestamp": time.time(),
            })
            context.conversation_history.append({
                "role": "assistant",
                "content": result.content,
                "mode": intent_analysis.mode.value,
                "framework": result.framework_used,
                "timestamp": time.time(),
            })

            # 7. Update metrics
            if self._config.enable_metrics:
                self._metrics.record_execution(
                    mode=intent_analysis.mode,
                    framework=result.framework_used,
                    success=result.success,
                    duration=time.time() - start_time,
                )

        except asyncio.TimeoutError:
            result = HybridResultV2(
                success=False,
                error=f"Execution timed out after {timeout or self._config.timeout}s",
                session_id=context.session_id,
                execution_mode=context.current_mode,
            )
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            result = HybridResultV2(
                success=False,
                error=str(e),
                session_id=context.session_id,
                execution_mode=context.current_mode,
            )

        result.duration = time.time() - start_time
        result.session_id = context.session_id
        result.intent_analysis = context.intent_analysis

        return result

    # =========================================================================
    # Phase 28 Execution Flow (Sprint 98)
    # =========================================================================

    async def execute_with_routing(
        self,
        request: IncomingRequest,
        *,
        session_id: Optional[str] = None,
        requester: str = "system",
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HybridResultV2:
        """
        Execute using Phase 28 routing flow.

        Sprint 98: New execution method integrating all Phase 28 components.

        Flow:
        1. InputGateway.process() → 來源識別和分流處理
        2. 檢查 completeness.is_sufficient
        3. GuidedDialogEngine → 資訊收集 (如需要)
        4. RiskAssessor.assess() → 風險評估
        5. HITLController → 審批 (如需要)
        6. FrameworkSelector.select_framework() → 框架選擇
        7. 執行 (Claude SDK / MAF)

        Args:
            request: Incoming request from InputGateway
            session_id: Optional session ID
            requester: User or system making the request
            timeout: Execution timeout in seconds
            metadata: Additional metadata

        Returns:
            HybridResultV2 with execution outcome

        Raises:
            ValueError: If required Phase 28 components are not configured
        """
        start_time = time.time()

        # Validate Phase 28 components
        if not self._input_gateway:
            raise ValueError("InputGateway not configured. Use execute() for basic execution.")

        # Get or create session
        if session_id and session_id in self._sessions:
            context = self._sessions[session_id]
        else:
            sid = self.create_session(session_id, metadata)
            context = self._sessions[sid]

        context.last_activity = time.time()

        try:
            # Step 1: InputGateway 處理
            logger.info(f"Phase 28 Step 1: Processing request via InputGateway")
            routing_decision = await self._input_gateway.process(request)

            # Step 2: 檢查完整度
            logger.info(f"Phase 28 Step 2: Checking completeness")
            if not routing_decision.completeness.is_sufficient:
                # Step 3: 啟動 GuidedDialog (如需要)
                if self._guided_dialog:
                    logger.info(f"Phase 28 Step 3: Starting guided dialog for missing info")
                    dialog_response = await self._handle_guided_dialog(
                        routing_decision, request, context
                    )
                    if dialog_response.needs_more_info:
                        return HybridResultV2(
                            success=True,
                            content=dialog_response.message,
                            session_id=context.session_id,
                            execution_mode=ExecutionMode.CHAT_MODE,
                            framework_used="guided_dialog",
                            metadata={
                                "dialog_id": dialog_response.dialog_id,
                                "questions": [q.dict() if hasattr(q, 'dict') else str(q)
                                             for q in (dialog_response.questions or [])],
                                "status": "pending_info",
                            },
                        )
                    # Update routing decision with new info
                    routing_decision = dialog_response.routing_decision or routing_decision

            # Step 4: 風險評估
            risk_assessment = None
            if self._risk_assessor:
                logger.info(f"Phase 28 Step 4: Assessing risk")
                risk_assessment = self._risk_assessor.assess(routing_decision)

            # Step 5: HITL 審批 (如需要)
            if risk_assessment and risk_assessment.requires_approval:
                if self._hitl_controller:
                    logger.info(f"Phase 28 Step 5: Starting HITL approval")
                    approval_result = await self._handle_hitl(
                        routing_decision, risk_assessment, requester
                    )
                    if approval_result.status == ApprovalStatus.PENDING:
                        return HybridResultV2(
                            success=True,
                            content="Operation requires approval. Waiting for authorization.",
                            session_id=context.session_id,
                            execution_mode=ExecutionMode.WORKFLOW_MODE,
                            framework_used="hitl_controller",
                            metadata={
                                "approval_id": approval_result.request_id,
                                "status": "pending_approval",
                            },
                        )
                    if approval_result.status == ApprovalStatus.REJECTED:
                        return HybridResultV2(
                            success=False,
                            content=f"Operation rejected: {approval_result.comment or 'No reason provided'}",
                            session_id=context.session_id,
                            execution_mode=ExecutionMode.WORKFLOW_MODE,
                            framework_used="hitl_controller",
                            error="Approval rejected",
                            metadata={
                                "approval_id": approval_result.request_id,
                                "status": "rejected",
                                "rejected_by": approval_result.rejected_by,
                            },
                        )

            # Step 6: 框架選擇
            logger.info(f"Phase 28 Step 6: Selecting framework")
            session_context = SessionContext(
                session_id=context.session_id,
                conversation_history=context.conversation_history,
                current_mode=context.current_mode,
            )
            framework_analysis = await self._framework_selector.select_framework(
                user_input=request.content,
                session_context=session_context,
                routing_decision=routing_decision,
            )

            context.intent_analysis = framework_analysis
            context.current_mode = framework_analysis.mode

            # Step 7: 執行
            logger.info(f"Phase 28 Step 7: Executing in mode {framework_analysis.mode}")
            if framework_analysis.mode == ExecutionMode.WORKFLOW_MODE:
                result = await self._execute_workflow_mode(
                    request.content,
                    context,
                    framework_analysis,
                    tools=None,
                    max_tokens=None,
                    timeout=timeout,
                )
            else:
                result = await self._execute_chat_mode(
                    request.content,
                    context,
                    framework_analysis,
                    tools=None,
                    max_tokens=None,
                    timeout=timeout,
                )

            # Update result metadata with routing info
            result.metadata = result.metadata or {}
            result.metadata.update({
                "routing_decision": routing_decision.to_dict() if hasattr(routing_decision, 'to_dict') else str(routing_decision),
                "risk_assessment": risk_assessment.to_dict() if risk_assessment and hasattr(risk_assessment, 'to_dict') else None,
                "phase_28_flow": True,
            })

            result.session_id = context.session_id
            result.duration = time.time() - start_time

            return result

        except Exception as e:
            logger.error(f"Phase 28 execution error: {e}", exc_info=True)
            return HybridResultV2(
                success=False,
                error=str(e),
                session_id=context.session_id,
                execution_mode=context.current_mode,
                duration=time.time() - start_time,
            )

    async def _handle_guided_dialog(
        self,
        routing_decision: RoutingDecision,
        request: IncomingRequest,
        context: ExecutionContextV2,
    ) -> DialogResponse:
        """
        Handle guided dialog for missing information.

        Args:
            routing_decision: Current routing decision
            request: Original incoming request
            context: Execution context

        Returns:
            DialogResponse with questions or updated routing decision
        """
        if not self._guided_dialog:
            raise ValueError("GuidedDialogEngine not configured")

        # Start dialog session
        response = await self._guided_dialog.start_dialog(
            request.content,
            initial_context={
                "routing_decision": routing_decision,
                "source_type": request.source_type.value if hasattr(request.source_type, 'value') else str(request.source_type),
                "session_id": context.session_id,
            },
        )

        return response

    async def _handle_hitl(
        self,
        routing_decision: RoutingDecision,
        risk_assessment: RiskAssessment,
        requester: str,
    ) -> ApprovalRequest:
        """
        Handle HITL approval workflow.

        Args:
            routing_decision: Routing decision requiring approval
            risk_assessment: Risk assessment for the operation
            requester: User requesting the operation

        Returns:
            ApprovalRequest with status
        """
        if not self._hitl_controller:
            raise ValueError("HITLController not configured")

        # Create approval request
        approval_request = await self._hitl_controller.request_approval(
            routing_decision=routing_decision,
            risk_assessment=risk_assessment,
            requester=requester,
        )

        return approval_request

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _prepare_hybrid_context(
        self,
        context: ExecutionContextV2,
        prompt: str,
    ) -> Optional[HybridContext]:
        """Prepare hybrid context for execution."""
        try:
            # Create or update hybrid context via bridge
            hybrid_context = await self._context_bridge.get_or_create_hybrid(
                session_id=context.session_id,
            )
            return hybrid_context
        except Exception as e:
            logger.warning(f"Failed to prepare hybrid context: {e}")
            return None

    async def _execute_workflow_mode(
        self,
        prompt: str,
        context: ExecutionContextV2,
        intent: IntentAnalysis,
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: Optional[int],
        timeout: Optional[float],
    ) -> HybridResultV2:
        """
        Execute in Workflow Mode.

        MAF 主導執行，但 Tool 透過 UnifiedToolExecutor。
        """
        logger.info(f"Executing in WORKFLOW_MODE: {prompt[:50]}...")

        if self._maf_executor:
            try:
                # Use MAF executor with tool callback if available
                raw_result = await asyncio.wait_for(
                    self._maf_executor(
                        prompt=prompt,
                        history=context.conversation_history,
                        tools=tools,
                        max_tokens=max_tokens,
                        tool_callback=self._maf_callback,
                    ),
                    timeout=timeout or self._config.timeout,
                )

                return self._convert_to_result_v2(
                    raw_result,
                    framework="microsoft_agent_framework",
                    mode=ExecutionMode.WORKFLOW_MODE,
                )
            except Exception as e:
                logger.error(f"Workflow mode execution error: {e}")
                return HybridResultV2(
                    success=False,
                    error=str(e),
                    framework_used="microsoft_agent_framework",
                    execution_mode=ExecutionMode.WORKFLOW_MODE,
                )
        elif self._claude_executor:
            # Fallback to Claude executor when MAF not available
            # Sprint 67: Enable workflow mode with Claude SDK as fallback
            logger.info("MAF executor not available, using Claude executor for workflow mode")
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

                return self._convert_to_result_v2(
                    raw_result,
                    framework="claude_sdk",
                    mode=ExecutionMode.WORKFLOW_MODE,
                )
            except asyncio.TimeoutError:
                # S67-BF-1: Explicit timeout error handling
                logger.error(f"Workflow mode (Claude fallback) timeout after {timeout or self._config.timeout}s")
                return HybridResultV2(
                    success=False,
                    error=f"Request timed out after {timeout or self._config.timeout} seconds. This may be due to API rate limiting.",
                    framework_used="claude_sdk",
                    execution_mode=ExecutionMode.WORKFLOW_MODE,
                )
            except Exception as e:
                # S67-BF-1: Enhanced error logging
                error_msg = str(e)
                if "429" in error_msg or "rate" in error_msg.lower():
                    logger.warning(f"Workflow mode (Claude fallback) rate limited: {e}")
                else:
                    logger.error(f"Workflow mode (Claude fallback) error: {e}", exc_info=True)
                return HybridResultV2(
                    success=False,
                    error=error_msg,
                    framework_used="claude_sdk",
                    execution_mode=ExecutionMode.WORKFLOW_MODE,
                )
        else:
            # Simulated response (only when no executor available)
            return HybridResultV2(
                success=True,
                content=f"[WORKFLOW_MODE] Processed: {prompt[:100]}...",
                framework_used="microsoft_agent_framework",
                execution_mode=ExecutionMode.WORKFLOW_MODE,
            )

    async def _execute_chat_mode(
        self,
        prompt: str,
        context: ExecutionContextV2,
        intent: IntentAnalysis,
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: Optional[int],
        timeout: Optional[float],
    ) -> HybridResultV2:
        """
        Execute in Chat Mode.

        Claude 主導執行，直接使用 Claude SDK。
        S75-5: Supports multimodal content for images, PDFs, and text files.
        """
        logger.info(f"Executing in CHAT_MODE: {prompt[:50]}...")

        if self._claude_executor:
            try:
                # S75-5: Check for multimodal content in metadata
                multimodal_content = context.metadata.get("multimodal_content")

                # Build executor kwargs
                executor_kwargs = {
                    "prompt": prompt,
                    "history": context.conversation_history,
                    "tools": tools,
                    "max_tokens": max_tokens,
                }

                # S75-5: Add multimodal_content if available
                if multimodal_content:
                    executor_kwargs["multimodal_content"] = multimodal_content
                    logger.info(f"[S75-5] Passing multimodal content to claude_executor: {len(multimodal_content)} blocks")

                raw_result = await asyncio.wait_for(
                    self._claude_executor(**executor_kwargs),
                    timeout=timeout or self._config.timeout,
                )

                return self._convert_to_result_v2(
                    raw_result,
                    framework="claude_sdk",
                    mode=ExecutionMode.CHAT_MODE,
                )
            except asyncio.TimeoutError:
                # S67-BF-1: Explicit timeout error handling
                logger.error(f"Chat mode timeout after {timeout or self._config.timeout}s")
                return HybridResultV2(
                    success=False,
                    error=f"Request timed out after {timeout or self._config.timeout} seconds. This may be due to API rate limiting.",
                    framework_used="claude_sdk",
                    execution_mode=ExecutionMode.CHAT_MODE,
                )
            except Exception as e:
                # S67-BF-1: Enhanced error logging
                error_msg = str(e)
                if "429" in error_msg or "rate" in error_msg.lower():
                    logger.warning(f"Chat mode rate limited: {e}")
                else:
                    logger.error(f"Chat mode execution error: {e}", exc_info=True)
                return HybridResultV2(
                    success=False,
                    error=error_msg,
                    framework_used="claude_sdk",
                    execution_mode=ExecutionMode.CHAT_MODE,
                )
        else:
            # Simulated response
            return HybridResultV2(
                success=True,
                content=f"[CHAT_MODE] Processed: {prompt[:100]}...",
                framework_used="claude_sdk",
                execution_mode=ExecutionMode.CHAT_MODE,
            )

    async def _execute_hybrid_mode(
        self,
        prompt: str,
        context: ExecutionContextV2,
        intent: IntentAnalysis,
        tools: Optional[List[Dict[str, Any]]],
        max_tokens: Optional[int],
        timeout: Optional[float],
    ) -> HybridResultV2:
        """
        Execute in Hybrid Mode.

        動態切換，根據執行過程中的需求調整。
        優先使用 Claude 處理，MAF 處理結構化部分。
        """
        logger.info(f"Executing in HYBRID_MODE: {prompt[:50]}...")

        # In hybrid mode, we start with Claude and may switch to MAF
        # for structured workflow parts
        suggested_framework = intent.suggested_framework

        if suggested_framework and suggested_framework.maf_confidence > 0.7:
            # Use MAF for structured parts
            result = await self._execute_workflow_mode(
                prompt, context, intent, tools, max_tokens, timeout
            )
            result.execution_mode = ExecutionMode.HYBRID_MODE
        else:
            # Use Claude for conversational parts
            result = await self._execute_chat_mode(
                prompt, context, intent, tools, max_tokens, timeout
            )
            result.execution_mode = ExecutionMode.HYBRID_MODE

        return result

    def _convert_to_result_v2(
        self,
        raw_result: Any,
        framework: str,
        mode: ExecutionMode,
    ) -> HybridResultV2:
        """
        Convert raw result to HybridResultV2.

        Sprint 66: S66-2 - Now converts tool_calls to tool_results for AG-UI events.
        """
        if isinstance(raw_result, HybridResultV2):
            return raw_result
        elif isinstance(raw_result, dict):
            # Convert tool_calls to ToolExecutionResult list
            tool_results: List[ToolExecutionResult] = []
            raw_tool_calls = raw_result.get("tool_calls", [])

            for tc in raw_tool_calls:
                if isinstance(tc, dict):
                    tool_results.append(
                        ToolExecutionResult(
                            success=True,  # Assume success if in result
                            content="",  # Content is in main result
                            tool_name=tc.get("name", ""),
                            execution_id=tc.get("id", str(uuid.uuid4())),
                            source=ToolSource.CLAUDE if framework == "claude_sdk" else ToolSource.MAF,
                            metadata={"args": tc.get("args", {})},
                        )
                    )
                elif hasattr(tc, "name"):
                    # Handle object-style tool calls
                    tool_results.append(
                        ToolExecutionResult(
                            success=True,
                            content="",
                            tool_name=getattr(tc, "name", ""),
                            execution_id=getattr(tc, "id", str(uuid.uuid4())),
                            source=ToolSource.CLAUDE if framework == "claude_sdk" else ToolSource.MAF,
                            metadata={"args": getattr(tc, "args", {})},
                        )
                    )

            return HybridResultV2(
                success=raw_result.get("success", True),
                content=raw_result.get("content", ""),
                error=raw_result.get("error"),
                framework_used=framework,
                execution_mode=mode,
                tokens_used=raw_result.get("tokens_used", 0),
                metadata=raw_result.get("metadata", {}),
                tool_results=tool_results,
            )
        else:
            return HybridResultV2(
                success=True,
                content=str(raw_result),
                framework_used=framework,
                execution_mode=mode,
            )

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        source: ToolSource = ToolSource.HYBRID,
        session_id: Optional[str] = None,
        approval_required: bool = False,
    ) -> ToolExecutionResult:
        """
        Execute a tool through unified executor.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            source: Source of the tool call
            session_id: Optional session ID
            approval_required: Whether approval is required

        Returns:
            ToolExecutionResult
        """
        if not self._unified_executor:
            return ToolExecutionResult(
                success=False,
                error="UnifiedToolExecutor not configured",
                tool_name=tool_name,
                source=source,
            )

        # Get hybrid context if session exists
        context = None
        if session_id and session_id in self._sessions:
            context = self._sessions[session_id].hybrid_context

        return await self._unified_executor.execute(
            tool_name=tool_name,
            arguments=arguments,
            source=source,
            context=context,
            approval_required=approval_required,
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics.reset()

    # V1 Compatibility Methods

    def analyze_task(self, prompt: str) -> IntentAnalysis:
        """
        Analyze a task without executing (V1 compat).

        Args:
            prompt: The task prompt to analyze

        Returns:
            IntentAnalysis with mode and confidence
        """
        # Synchronous wrapper for async method
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self._framework_selector.analyze_intent(prompt)
            )
        finally:
            loop.close()

    def set_claude_executor(self, executor: Callable) -> None:
        """Set the Claude SDK executor (V1 compat)."""
        self._claude_executor = executor

    def set_maf_executor(self, executor: Callable) -> None:
        """Set the MAF executor (V1 compat)."""
        self._maf_executor = executor


@dataclass
class OrchestratorMetrics:
    """Metrics for HybridOrchestratorV2."""

    execution_count: int = 0
    total_duration: float = 0.0
    mode_usage: Dict[str, int] = field(default_factory=lambda: {
        "WORKFLOW_MODE": 0,
        "CHAT_MODE": 0,
        "HYBRID_MODE": 0,
    })
    framework_usage: Dict[str, int] = field(default_factory=lambda: {
        "claude_sdk": 0,
        "microsoft_agent_framework": 0,
    })
    success_count: int = 0
    failure_count: int = 0

    def record_execution(
        self,
        mode: ExecutionMode,
        framework: str,
        success: bool,
        duration: float,
    ) -> None:
        """Record an execution."""
        self.execution_count += 1
        self.total_duration += duration
        self.mode_usage[mode.name] = self.mode_usage.get(mode.name, 0) + 1
        self.framework_usage[framework] = self.framework_usage.get(framework, 0) + 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

    def reset(self) -> None:
        """Reset all metrics."""
        self.execution_count = 0
        self.total_duration = 0.0
        self.mode_usage = {
            "WORKFLOW_MODE": 0,
            "CHAT_MODE": 0,
            "HYBRID_MODE": 0,
        }
        self.framework_usage = {
            "claude_sdk": 0,
            "microsoft_agent_framework": 0,
        }
        self.success_count = 0
        self.failure_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        avg_duration = (
            self.total_duration / self.execution_count
            if self.execution_count > 0
            else 0.0
        )
        success_rate = (
            self.success_count / self.execution_count
            if self.execution_count > 0
            else 0.0
        )
        return {
            "execution_count": self.execution_count,
            "total_duration": self.total_duration,
            "avg_duration": avg_duration,
            "mode_usage": dict(self.mode_usage),
            "framework_usage": dict(self.framework_usage),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
        }


def create_orchestrator_v2(
    *,
    mode: OrchestratorMode = OrchestratorMode.V2_FULL,
    primary_framework: str = "claude_sdk",
    auto_switch: bool = True,
    intent_router: Optional[IntentRouter] = None,
    context_bridge: Optional[ContextBridge] = None,
    unified_executor: Optional[UnifiedToolExecutor] = None,
) -> HybridOrchestratorV2:
    """
    Factory function to create a HybridOrchestratorV2.

    Args:
        mode: Orchestrator operation mode
        primary_framework: Default framework
        auto_switch: Whether to auto-switch modes
        intent_router: Optional custom IntentRouter
        context_bridge: Optional custom ContextBridge
        unified_executor: Optional custom UnifiedToolExecutor

    Returns:
        Configured HybridOrchestratorV2 instance
    """
    config = OrchestratorConfig(
        mode=mode,
        primary_framework=primary_framework,
        auto_switch=auto_switch,
    )

    return HybridOrchestratorV2(
        config=config,
        intent_router=intent_router,
        context_bridge=context_bridge,
        unified_executor=unified_executor,
    )
