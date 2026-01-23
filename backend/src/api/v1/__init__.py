# =============================================================================
# IPA Platform - API v1 Module
# =============================================================================
# Sprint 4: Developer Experience - Complete Developer Tools
# Phase 2: Advanced Orchestration
#   - Sprint 7: Concurrent Execution Engine
#   - Sprint 8: Agent Handoff & Collaboration
#   - Sprint 9: GroupChat & Multi-turn Conversation
#   - Sprint 10: Dynamic Planning & Autonomous Decision
#   - Sprint 11: Nested Workflows & Advanced Orchestration
#   - Sprint 12: Integration & Polish
#
# API version 1 module aggregating all route modules.
# Includes:
#   - agents: Agent CRUD and execution
#   - workflows: Workflow CRUD and validation
#   - executions: Execution tracking and state management
#   - checkpoints: Human-in-the-loop checkpoint management
#   - connectors: Cross-system connector management
#   - cache: LLM response caching
#   - triggers: Webhook trigger management (n8n integration)
#   - prompts: Prompt template management
#   - audit: Audit logging and compliance
#   - notifications: Teams notification integration
#   - routing: Cross-scenario routing
#   - templates: Agent template marketplace (Sprint 4)
#   - learning: Few-shot learning mechanism (Sprint 4)
#   - devtools: Execution tracing and debugging (Sprint 4)
#   - versioning: Template version management (Sprint 4)
#   - concurrent: Concurrent execution with Fork-Join (Sprint 7)
#   - handoff: Agent handoff and collaboration (Sprint 8)
#   - groupchat: GroupChat and multi-turn conversation (Sprint 9)
#   - planning: Dynamic planning and autonomous decision (Sprint 10)
#   - nested: Nested workflows and advanced orchestration (Sprint 11)
#   - performance: Performance monitoring and optimization (Sprint 12)
#   - code_interpreter: Code Interpreter integration (Sprint 37)
#   - mcp: MCP Architecture - Server management, tool discovery (Sprint 39-41)
#   - sessions: Session Mode - Multi-turn conversation management (Sprint 42-44)
#   - claude_sdk: Claude Agent SDK Integration (Sprint 48-51)
#   - hybrid: Hybrid Context Bridge (Sprint 53)
#   - hybrid/risk: Risk Assessment API (Sprint 55)
#   - hybrid/switch: Mode Switcher API (Sprint 56)
#   - auth: Authentication API (Sprint 70)
#   - files: File Upload API (Sprint 75)
#   - memory: Memory System API (Sprint 79)
# =============================================================================

from fastapi import APIRouter

from src.api.v1.agents.routes import router as agents_router
from src.api.v1.auth import router as auth_router  # Sprint 70: Authentication
from src.api.v1.files import router as files_router  # Sprint 75: File Upload
from src.api.v1.memory import router as memory_router  # Sprint 79: Memory System
from src.api.v1.code_interpreter.routes import router as code_interpreter_router
from src.api.v1.audit.routes import router as audit_router
from src.api.v1.audit.decision_routes import router as decision_audit_router  # Sprint 80: Decision Audit
from src.api.v1.cache.routes import router as cache_router
from src.api.v1.checkpoints.routes import router as checkpoints_router
from src.api.v1.concurrent.routes import router as concurrent_router
from src.api.v1.connectors.routes import router as connectors_router
from src.api.v1.dashboard.routes import router as dashboard_router
from src.api.v1.devtools.routes import router as devtools_router
from src.api.v1.executions.routes import router as executions_router
from src.api.v1.groupchat.routes import router as groupchat_router
from src.api.v1.handoff.routes import router as handoff_router
from src.api.v1.learning.routes import router as learning_router
from src.api.v1.mcp.routes import router as mcp_router
from src.api.v1.sessions import router as sessions_router  # Sprint 42-47: Session + Chat + WebSocket
from src.api.v1.nested.routes import router as nested_router
from src.api.v1.notifications.routes import router as notifications_router
from src.api.v1.performance.routes import router as performance_router
from src.api.v1.planning.routes import router as planning_router
from src.api.v1.prompts.routes import router as prompts_router
from src.api.v1.routing.routes import router as routing_router
from src.api.v1.templates.routes import router as templates_router
from src.api.v1.triggers.routes import router as triggers_router
from src.api.v1.versioning.routes import router as versioning_router
from src.api.v1.workflows.routes import router as workflows_router
from src.api.v1.claude_sdk import router as claude_sdk_router  # Sprint 48-51: Claude SDK
from src.api.v1.hybrid import context_router as hybrid_context_router  # Sprint 53: Hybrid Context
from src.api.v1.hybrid import core_router as hybrid_core_router  # Sprint 52-54: Hybrid Core (analyze, execute, metrics)
from src.api.v1.hybrid import risk_router as hybrid_risk_router  # Sprint 55: Risk Assessment
from src.api.v1.hybrid import switch_router as hybrid_switch_router  # Sprint 56: Mode Switcher
from src.api.v1.ag_ui import router as ag_ui_router  # Sprint 58: AG-UI SSE Endpoint

# Phase 21: Sandbox Security
from src.api.v1.sandbox import router as sandbox_router  # Sprint 77-78: Sandbox Security

# Phase 22: Autonomous Planning
from src.api.v1.autonomous import router as autonomous_router  # Sprint 79: Autonomous Planning

# Phase 23: Multi-Agent Coordination
from src.api.v1.a2a.routes import router as a2a_router  # Sprint 81: A2A Protocol
from src.api.v1.patrol.routes import router as patrol_router  # Sprint 82: Patrol Mode
from src.api.v1.correlation.routes import router as correlation_router  # Sprint 82: Correlation Analysis
from src.api.v1.rootcause import router as rootcause_router  # Sprint 82: Root Cause Analysis

# Phase 28: Three-Tier Routing Architecture
from src.api.v1.orchestration import router as orchestration_router  # Sprint 96: Intent Classification
from src.api.v1.orchestration import intent_router as orchestration_intent_router  # Sprint 96: Intent API
from src.api.v1.orchestration import dialog_router as orchestration_dialog_router  # Sprint 98: Guided Dialog
from src.api.v1.orchestration import approval_router as orchestration_approval_router  # Sprint 98: HITL Approval

# Create main v1 router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers - Phase 1 (MVP)
api_router.include_router(dashboard_router)
api_router.include_router(agents_router)
api_router.include_router(workflows_router)
api_router.include_router(executions_router)
api_router.include_router(checkpoints_router)
api_router.include_router(connectors_router)
api_router.include_router(cache_router)
api_router.include_router(triggers_router)
api_router.include_router(prompts_router)
api_router.include_router(audit_router)
api_router.include_router(notifications_router)
api_router.include_router(routing_router)
api_router.include_router(templates_router)
api_router.include_router(learning_router)
api_router.include_router(devtools_router)
api_router.include_router(versioning_router)

# Include sub-routers - Phase 2 (Advanced Orchestration)
api_router.include_router(concurrent_router)   # Sprint 7: Concurrent Execution
api_router.include_router(handoff_router)      # Sprint 8: Agent Handoff
api_router.include_router(groupchat_router)    # Sprint 9: GroupChat
api_router.include_router(planning_router)     # Sprint 10: Dynamic Planning
api_router.include_router(nested_router)       # Sprint 11: Nested Workflows
api_router.include_router(performance_router)  # Sprint 12: Performance Monitoring

# Include sub-routers - Phase 8 (Code Interpreter Integration)
api_router.include_router(code_interpreter_router)  # Sprint 37: Code Interpreter

# Include sub-routers - Phase 9 (MCP Architecture)
api_router.include_router(mcp_router)  # Sprint 39-41: MCP Architecture

# Include sub-routers - Phase 10 (Session Mode)
api_router.include_router(sessions_router)  # Sprint 42-44: Session Management

# Include sub-routers - Phase 12 (Claude Agent SDK Integration)
api_router.include_router(claude_sdk_router)  # Sprint 48-51: Claude SDK

# Include sub-routers - Phase 13 (Hybrid MAF + Claude SDK Architecture)
api_router.include_router(hybrid_context_router)  # Sprint 53: Hybrid Context Bridge
api_router.include_router(hybrid_core_router)  # Sprint 52-54: Hybrid Core (analyze, execute, metrics)

# Include sub-routers - Phase 14 (HITL & Approval)
api_router.include_router(hybrid_risk_router)  # Sprint 55: Risk Assessment
api_router.include_router(hybrid_switch_router)  # Sprint 56: Mode Switcher

# Include sub-routers - Phase 15 (AG-UI Integration)
api_router.include_router(ag_ui_router)  # Sprint 58: AG-UI SSE Endpoint

# Include sub-routers - Phase 18 (Authentication System)
api_router.include_router(auth_router)  # Sprint 70: Authentication

# Include sub-routers - Phase 20 (File Attachment Support)
api_router.include_router(files_router)  # Sprint 75: File Upload

# Include sub-routers - Phase 22 (Claude 自主能力與學習系統)
api_router.include_router(memory_router)  # Sprint 79: Memory System
api_router.include_router(decision_audit_router)  # Sprint 80: Decision Audit

# Include sub-routers - Phase 21 (Sandbox Security)
api_router.include_router(sandbox_router)  # Sprint 77-78: Sandbox Security

# Include sub-routers - Phase 22 (Autonomous Planning)
api_router.include_router(autonomous_router)  # Sprint 79: Autonomous Planning

# Include sub-routers - Phase 23 (Multi-Agent Coordination)
api_router.include_router(a2a_router)  # Sprint 81: A2A Protocol
api_router.include_router(patrol_router)  # Sprint 82: Patrol Mode
api_router.include_router(correlation_router)  # Sprint 82: Correlation Analysis
api_router.include_router(rootcause_router)  # Sprint 82: Root Cause Analysis

# Include sub-routers - Phase 28 (Three-Tier Routing Architecture)
api_router.include_router(orchestration_router)  # Sprint 96: Orchestration & Policies
api_router.include_router(orchestration_intent_router)  # Sprint 96: Intent Classification
api_router.include_router(orchestration_dialog_router)  # Sprint 98: Guided Dialog
api_router.include_router(orchestration_approval_router)  # Sprint 98: HITL Approval

__all__ = ["api_router"]
