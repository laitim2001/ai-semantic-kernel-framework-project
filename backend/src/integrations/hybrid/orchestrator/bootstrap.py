"""OrchestratorBootstrap — full pipeline assembly at startup.

Wires all 7 handlers with their real dependencies and returns a
fully-connected OrchestratorMediator instance. Replaces the previous
pattern where all handlers defaulted to None.

Sprint 134 — Phase 39 E2E Assembly D.
"""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
from src.integrations.hybrid.orchestrator.agent_handler import AgentHandler
from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry

logger = logging.getLogger(__name__)


class OrchestratorBootstrap:
    """Factory that assembles a fully-wired OrchestratorMediator.

    Usage::

        bootstrap = OrchestratorBootstrap()
        mediator = bootstrap.build()
        # mediator now has all 7 handlers wired to real dependencies

    All wiring methods use graceful degradation — if a dependency is
    unavailable (ImportError, missing config), the handler is still
    created with a None dependency and a warning is logged.
    """

    def __init__(self, llm_service: Any = None) -> None:
        self._llm_service = llm_service
        self._tool_registry: Optional[OrchestratorToolRegistry] = None
        self._components: Dict[str, Any] = {}

    def build(self) -> OrchestratorMediator:
        """Assemble and return a fully-wired OrchestratorMediator.

        Wires all 7 handlers in dependency order:
        1. ContextHandler (no deps)
        2. RoutingHandler (InputGateway + IntentRouter + FrameworkSelector)
        3. DialogHandler (GuidedDialogEngine)
        4. ApprovalHandler (RiskAssessor + HITLController)
        5. AgentHandler (LLM + ToolRegistry)
        6. ExecutionHandler (MAF + Claude + Swarm executors)
        7. ObservabilityHandler (Metrics)
        """
        logger.info("OrchestratorBootstrap: starting full pipeline assembly...")

        # Ensure LLM service
        if self._llm_service is None:
            self._llm_service = self._create_llm_service()

        # Ensure tool registry with handlers
        self._tool_registry = self._create_tool_registry()

        # Wire all 7 handlers
        context_handler = self._wire_context_handler()
        routing_handler = self._wire_routing_handler()
        dialog_handler = self._wire_dialog_handler()
        approval_handler = self._wire_approval_handler()
        agent_handler = self._wire_agent_handler()
        execution_handler = self._wire_execution_handler()
        observability_handler = self._wire_observability_handler()

        # Register MCP tools
        self._wire_mcp_tools()

        # Assemble mediator
        mediator = OrchestratorMediator(
            routing_handler=routing_handler,
            dialog_handler=dialog_handler,
            approval_handler=approval_handler,
            agent_handler=agent_handler,
            execution_handler=execution_handler,
            context_handler=context_handler,
            observability_handler=observability_handler,
        )

        # Store references for health check
        self._components = {
            "context_handler": context_handler,
            "routing_handler": routing_handler,
            "dialog_handler": dialog_handler,
            "approval_handler": approval_handler,
            "agent_handler": agent_handler,
            "execution_handler": execution_handler,
            "observability_handler": observability_handler,
            "tool_registry": self._tool_registry,
            "llm_service": self._llm_service,
        }

        wired = sum(1 for v in self._components.values() if v is not None)
        logger.info(
            "OrchestratorBootstrap: assembly complete — %d/%d components wired",
            wired, len(self._components),
        )
        return mediator

    def health_check(self) -> Dict[str, Any]:
        """Verify all handlers are correctly wired."""
        results: Dict[str, str] = {}
        for name, component in self._components.items():
            if component is None:
                results[name] = "NOT_WIRED"
            else:
                results[name] = "OK"

        all_ok = all(v == "OK" for v in results.values())
        return {
            "status": "healthy" if all_ok else "degraded",
            "components": results,
            "wired_count": sum(1 for v in results.values() if v == "OK"),
            "total_count": len(results),
        }

    @property
    def tool_registry(self) -> Optional[OrchestratorToolRegistry]:
        """Access the wired tool registry."""
        return self._tool_registry

    # ------------------------------------------------------------------
    # LLM Service
    # ------------------------------------------------------------------

    @staticmethod
    def _create_llm_service() -> Any:
        """Create LLM service via factory."""
        try:
            from src.integrations.llm.factory import LLMServiceFactory
            service = LLMServiceFactory.create(use_cache=True, cache_ttl=1800)
            logger.info("Bootstrap: LLM service created")
            return service
        except Exception as e:
            logger.warning("Bootstrap: LLM service unavailable: %s", e)
            return None

    # ------------------------------------------------------------------
    # Tool Registry with dispatch handlers
    # ------------------------------------------------------------------

    def _create_tool_registry(self) -> OrchestratorToolRegistry:
        """Create tool registry and wire dispatch handlers."""
        # Sprint 137: Wire ToolSecurityGateway
        security_gateway = None
        try:
            from src.core.security.tool_gateway import ToolSecurityGateway
            security_gateway = ToolSecurityGateway()
            logger.info("Bootstrap: ToolSecurityGateway wired into ToolRegistry")
        except Exception as e:
            logger.warning("Bootstrap: ToolSecurityGateway unavailable: %s", e)

        registry = OrchestratorToolRegistry(security_gateway=security_gateway)
        try:
            from src.integrations.hybrid.orchestrator.dispatch_handlers import (
                DispatchHandlers,
            )
            from src.domain.tasks.service import TaskService
            from src.infrastructure.storage.task_store import TaskStore
            from src.integrations.hybrid.orchestrator.result_synthesiser import (
                ResultSynthesiser,
            )

            task_store = TaskStore()
            task_service = TaskService(task_store=task_store)
            synthesiser = ResultSynthesiser(llm_service=self._llm_service)
            handlers = DispatchHandlers(
                task_service=task_service,
                result_synthesiser=synthesiser,
            )
            handlers.register_all(registry)
            logger.info("Bootstrap: dispatch handlers registered (%d tools)", len(registry._handlers))
        except Exception as e:
            logger.warning("Bootstrap: dispatch handlers failed: %s", e)
        return registry

    # ------------------------------------------------------------------
    # Handler wiring methods
    # ------------------------------------------------------------------

    def _wire_context_handler(self) -> Any:
        """Wire ContextHandler with ContextBridge + MemoryManager."""
        try:
            from src.integrations.hybrid.orchestrator.handlers.context import ContextHandler
            context_bridge = None
            try:
                from src.integrations.hybrid.context.bridge import ContextBridge
                context_bridge = ContextBridge()
            except Exception as e:
                logger.warning("Bootstrap: ContextBridge unavailable: %s", e)

            # Sprint 135/144: Wire MemoryManager with memory_client
            memory_manager = None
            try:
                from src.integrations.hybrid.orchestrator.memory_manager import (
                    OrchestratorMemoryManager,
                )
                conv_store = None
                try:
                    from src.infrastructure.storage.conversation_state import (
                        ConversationStateStore,
                    )
                    conv_store = ConversationStateStore()
                except Exception:
                    pass

                # Sprint 144: Connect UnifiedMemoryManager as memory_client
                memory_client = None
                try:
                    from src.integrations.memory.unified_memory import (
                        UnifiedMemoryManager,
                    )
                    memory_client = UnifiedMemoryManager()
                    logger.info("Bootstrap: UnifiedMemoryManager created as memory_client")
                except Exception as mem_err:
                    logger.warning("Bootstrap: UnifiedMemoryManager unavailable: %s", mem_err)

                memory_manager = OrchestratorMemoryManager(
                    llm_service=self._llm_service,
                    memory_client=memory_client,
                    conversation_store=conv_store,
                )
                logger.info(
                    "Bootstrap: MemoryManager created (memory_client=%s)",
                    memory_client is not None,
                )
            except Exception as e:
                logger.warning("Bootstrap: MemoryManager unavailable: %s", e)

            handler = ContextHandler(
                context_bridge=context_bridge,
                memory_manager=memory_manager,
            )
            logger.info(
                "Bootstrap: ContextHandler wired (bridge=%s, memory=%s)",
                context_bridge is not None,
                memory_manager is not None,
            )
            return handler
        except Exception as e:
            logger.error("Bootstrap: ContextHandler failed: %s", e)
            return None

    def _wire_routing_handler(self) -> Any:
        """Wire RoutingHandler with InputGateway + IntentRouter + FrameworkSelector."""
        try:
            from src.integrations.hybrid.orchestrator.handlers.routing import RoutingHandler

            # InputGateway (Sprint 144: register source handlers via factory)
            input_gateway = None
            try:
                from src.integrations.orchestration.input_gateway.gateway import (
                    InputGateway,
                    create_input_gateway,
                )
                try:
                    input_gateway = create_input_gateway(
                        business_router=None,  # will be set below
                    )
                    logger.info("Bootstrap: InputGateway created with source handlers")
                except Exception:
                    # Fallback: create basic gateway with empty handlers
                    input_gateway = InputGateway(source_handlers={})
                    logger.info("Bootstrap: InputGateway created (basic)")
            except Exception as e:
                logger.warning("Bootstrap: InputGateway unavailable: %s", e)

            # BusinessIntentRouter
            business_router = None
            try:
                from src.integrations.orchestration.intent_router.router import (
                    create_router_with_llm,
                )
                business_router = create_router_with_llm()
            except Exception as e:
                logger.warning("Bootstrap: BusinessIntentRouter unavailable: %s", e)

            # FrameworkSelector with classifiers (Sprint 144)
            framework_selector = None
            try:
                from src.integrations.hybrid.intent.router import FrameworkSelector
                from src.integrations.hybrid.intent.classifiers.rule_based import (
                    RuleBasedClassifier,
                )
                from src.integrations.hybrid.intent.classifiers.routing_decision import (
                    RoutingDecisionClassifier,
                )
                classifiers = [
                    RuleBasedClassifier(weight=1.0),
                    RoutingDecisionClassifier(weight=1.5),
                ]
                framework_selector = FrameworkSelector(
                    classifiers=classifiers,
                    confidence_threshold=0.6,
                )
                logger.info(
                    "Bootstrap: FrameworkSelector with %d classifiers",
                    len(classifiers),
                )
            except Exception as e:
                logger.warning("Bootstrap: FrameworkSelector unavailable: %s", e)

            # SwarmHandler
            swarm_handler = None
            try:
                from src.integrations.hybrid.swarm_mode import SwarmModeHandler
                swarm_handler = SwarmModeHandler()
            except Exception as e:
                logger.warning("Bootstrap: SwarmModeHandler unavailable: %s", e)

            handler = RoutingHandler(
                input_gateway=input_gateway,
                business_router=business_router,
                framework_selector=framework_selector,
                swarm_handler=swarm_handler,
            )
            logger.info(
                "Bootstrap: RoutingHandler wired (gateway=%s, router=%s, selector=%s, swarm=%s)",
                input_gateway is not None,
                business_router is not None,
                framework_selector is not None,
                swarm_handler is not None,
            )
            return handler
        except Exception as e:
            logger.error("Bootstrap: RoutingHandler failed: %s", e)
            return None

    def _wire_dialog_handler(self) -> Any:
        """Wire DialogHandler with GuidedDialogEngine."""
        try:
            from src.integrations.hybrid.orchestrator.handlers.dialog import DialogHandler
            guided_dialog = None
            try:
                from src.integrations.orchestration.guided_dialog.engine import GuidedDialogEngine
                guided_dialog = GuidedDialogEngine()
            except Exception as e:
                logger.warning("Bootstrap: GuidedDialogEngine unavailable: %s", e)

            handler = DialogHandler(guided_dialog=guided_dialog)
            logger.info("Bootstrap: DialogHandler wired (dialog=%s)", guided_dialog is not None)
            return handler
        except Exception as e:
            logger.error("Bootstrap: DialogHandler failed: %s", e)
            return None

    def _wire_approval_handler(self) -> Any:
        """Wire ApprovalHandler with RiskAssessor + HITLController."""
        try:
            from src.integrations.hybrid.orchestrator.handlers.approval import ApprovalHandler

            risk_assessor = None
            try:
                from src.integrations.orchestration.risk_assessor.assessor import RiskAssessor
                risk_assessor = RiskAssessor()
            except Exception as e:
                logger.warning("Bootstrap: RiskAssessor unavailable: %s", e)

            hitl_controller = None
            try:
                from src.integrations.orchestration.hitl.controller import HITLController
                hitl_controller = HITLController()
            except Exception as e:
                logger.warning("Bootstrap: HITLController unavailable: %s", e)

            handler = ApprovalHandler(
                risk_assessor=risk_assessor,
                hitl_controller=hitl_controller,
            )
            logger.info(
                "Bootstrap: ApprovalHandler wired (risk=%s, hitl=%s)",
                risk_assessor is not None,
                hitl_controller is not None,
            )
            return handler
        except Exception as e:
            logger.error("Bootstrap: ApprovalHandler failed: %s", e)
            return None

    def _wire_agent_handler(self) -> Any:
        """Wire AgentHandler with LLM + ToolRegistry."""
        try:
            handler = AgentHandler(
                llm_service=self._llm_service,
                tool_registry=self._tool_registry,
            )
            logger.info(
                "Bootstrap: AgentHandler wired (llm=%s, tools=%d)",
                self._llm_service is not None,
                len(self._tool_registry.list_tools(role="admin")) if self._tool_registry else 0,
            )
            return handler
        except Exception as e:
            logger.error("Bootstrap: AgentHandler failed: %s", e)
            return None

    def _wire_execution_handler(self) -> Any:
        """Wire ExecutionHandler with MAF + Claude + Swarm executors."""
        try:
            from src.integrations.hybrid.orchestrator.handlers.execution import ExecutionHandler

            claude_executor = None
            try:
                from src.integrations.claude_sdk.orchestrator.coordinator import ClaudeCoordinator
                coordinator = ClaudeCoordinator()
                claude_executor = coordinator.coordinate_agents
            except Exception as e:
                logger.warning("Bootstrap: Claude executor unavailable: %s", e)

            maf_executor = None
            try:
                from src.integrations.agent_framework.builders.workflow_executor import (
                    WorkflowExecutorAdapter,
                )
                adapter = WorkflowExecutorAdapter(id="orchestrator-maf-executor")
                maf_executor = adapter.run if hasattr(adapter, "run") else None
            except Exception as e:
                logger.warning("Bootstrap: MAF executor unavailable: %s", e)

            swarm_handler = None
            try:
                from src.integrations.hybrid.swarm_mode import SwarmModeHandler
                swarm_handler = SwarmModeHandler()
            except Exception as e:
                logger.warning("Bootstrap: SwarmHandler unavailable: %s", e)

            handler = ExecutionHandler(
                claude_executor=claude_executor,
                maf_executor=maf_executor,
                swarm_handler=swarm_handler,
            )
            logger.info(
                "Bootstrap: ExecutionHandler wired (claude=%s, maf=%s, swarm=%s)",
                claude_executor is not None,
                maf_executor is not None,
                swarm_handler is not None,
            )
            return handler
        except Exception as e:
            logger.error("Bootstrap: ExecutionHandler failed: %s", e)
            return None

    def _wire_observability_handler(self) -> Any:
        """Wire ObservabilityHandler with metrics."""
        try:
            from src.integrations.hybrid.orchestrator.handlers.observability import (
                ObservabilityHandler,
            )
            metrics = None
            try:
                from src.integrations.hybrid.orchestrator.observability_bridge import (
                    ObservabilityBridge,
                )
                metrics = ObservabilityBridge()
            except Exception as e:
                logger.warning("Bootstrap: ObservabilityBridge unavailable: %s", e)

            handler = ObservabilityHandler(metrics=metrics)
            logger.info("Bootstrap: ObservabilityHandler wired (metrics=%s)", metrics is not None)
            return handler
        except Exception as e:
            logger.error("Bootstrap: ObservabilityHandler failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # MCP Tool Bridge
    # ------------------------------------------------------------------

    def _wire_mcp_tools(self) -> None:
        """Discover and register MCP tools into the OrchestratorToolRegistry."""
        if self._tool_registry is None:
            return
        try:
            from src.integrations.hybrid.orchestrator.mcp_tool_bridge import MCPToolBridge
            bridge = MCPToolBridge(tool_registry=self._tool_registry)
            registered = bridge.discover_and_register()
            if registered > 0:
                logger.info("Bootstrap: %d MCP tools registered", registered)
        except ImportError:
            logger.info("Bootstrap: MCPToolBridge not available, skipping MCP tools")
        except Exception as e:
            logger.warning("Bootstrap: MCP tool registration failed: %s", e)
