# IPA Platform - Scenario-Based Feature Diagrams

> **Purpose**: 透過完整的業務場景流程圖展示 IPA Platform 所有已實現功能
> **Last Updated**: 2025-12-29

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Scenario 1: Enterprise Customer Service Automation](#scenario-1-enterprise-customer-service-automation)
3. [Scenario 2: Intelligent Document Processing Pipeline](#scenario-2-intelligent-document-processing-pipeline)
4. [Scenario 3: AI-Powered Decision Support System](#scenario-3-ai-powered-decision-support-system)
5. [Scenario 4: Multi-Agent Research Assistant](#scenario-4-multi-agent-research-assistant)
6. [Feature Module Relationship](#5-feature-module-relationship)
7. [Complete Data Flow](#6-complete-data-flow)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              IPA Platform Architecture                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         Frontend Layer (React 18)                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│  │  │Dashboard │ │ Agents   │ │Workflows │ │Executions│ │ Sessions │      │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                              REST API / WebSocket                               │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        API Layer (FastAPI)                               │   │
│  │  ┌────────────────────────────────────────────────────────────────┐     │   │
│  │  │ /api/v1/agents  /workflows  /executions  /sessions  /claude_sdk│     │   │
│  │  │ /groupchat  /handoff  /concurrent  /nested  /planning  /mcp    │     │   │
│  │  └────────────────────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Integration Layer (Adapters)                          │   │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────┐       │   │
│  │  │  Microsoft Agent Framework  │  │      Claude Agent SDK       │       │   │
│  │  │  ├─ GroupChatBuilder       │  │  ├─ ClaudeSDKClient         │       │   │
│  │  │  ├─ HandoffBuilder         │  │  ├─ ToolRegistry            │       │   │
│  │  │  ├─ ConcurrentBuilder      │  │  ├─ HookManager             │       │   │
│  │  │  ├─ MagenticBuilder        │  │  └─ HybridOrchestrator      │       │   │
│  │  │  ├─ WorkflowExecutor       │  ├─────────────────────────────┤       │   │
│  │  │  └─ CheckpointStorage      │  │        MCP Protocol         │       │   │
│  │  └─────────────────────────────┘  │  ├─ Shell Server           │       │   │
│  │                                    │  ├─ Filesystem Server      │       │   │
│  │                                    │  ├─ SSH Server             │       │   │
│  │                                    │  └─ LDAP Server            │       │   │
│  │                                    └─────────────────────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Domain Layer (Business Logic)                       │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │   │
│  │  │   Agent    │ │  Workflow  │ │ Execution  │ │  Session   │           │   │
│  │  │  Service   │ │  Service   │ │  Service   │ │  Service   │           │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │   │
│  │  │   State    │ │ Checkpoint │ │  Decision  │ │   File     │           │   │
│  │  │  Machine   │ │   System   │ │   Engine   │ │  Analyzer  │           │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Infrastructure Layer                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │   │
│  │  │  PostgreSQL  │  │    Redis     │  │   RabbitMQ   │                   │   │
│  │  │  (Persist)   │  │   (Cache)    │  │  (Messaging) │                   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Feature Modules at a Glance

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           IPA Platform Feature Map                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─ CORE ENGINE ─────────────────────────────────────────────────────────────┐  │
│  │                                                                            │  │
│  │  [Agent Management]     [Workflow Engine]      [Execution Control]        │  │
│  │   • CRUD Operations      • State Machine        • Status Tracking         │  │
│  │   • Configuration        • Step Execution       • History Management      │  │
│  │   • Capability Registry  • Error Handling       • Real-time Updates       │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌─ ORCHESTRATION ───────────────────────────────────────────────────────────┐  │
│  │                                                                            │  │
│  │  [GroupChat]           [Handoff]              [Concurrent]                │  │
│  │   • Multi-Agent Chat    • 3 Handoff Policies   • Parallel Execution       │  │
│  │   • Turn Management     • 6 Trigger Types      • Resource Pooling         │  │
│  │   • History Tracking    • Capability Match     • Error Isolation          │  │
│  │                                                                            │  │
│  │  [Nested Workflow]     [Dynamic Planning]      [MultiTurn]                │  │
│  │   • Sub-workflow Call   • Task Decomposition   • Conversation State       │  │
│  │   • Context Propagation • Plan Adaptation      • Memory Persistence       │  │
│  │   • Nested Error Handle • Autonomous Decision  • Checkpoint Storage       │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌─ AI ENHANCEMENT ──────────────────────────────────────────────────────────┐  │
│  │                                                                            │  │
│  │  [Decision Engine]     [Code Interpreter]      [LLM Integration]          │  │
│  │   • Confidence Scoring  • Sandbox Execution    • Azure OpenAI             │  │
│  │   • Multi-factor        • File Upload/Download • Response Caching         │  │
│  │   • Audit Trail         • Visualization Gen    • Token Tracking           │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌─ MCP & TOOLS ─────────────────────────────────────────────────────────────┐  │
│  │                                                                            │  │
│  │  [MCP Protocol]        [MCP Servers]           [Tool Management]          │  │
│  │   • Server Registry     • Shell (Security)     • Tool Discovery           │  │
│  │   • Transport Layer     • Filesystem (Sandbox) • Schema Validation        │  │
│  │   • Error Handling      • SSH (Connection Pool)• Execution Pipeline       │  │
│  │                         • LDAP (TLS Support)                              │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌─ SESSION & CLAUDE SDK ────────────────────────────────────────────────────┐  │
│  │                                                                            │  │
│  │  [Session Management]  [Agent-Session Bridge]  [Claude SDK]               │  │
│  │   • Session State       • AgentExecutor        • ClaudeSDKClient          │  │
│  │   • Message Tracking    • StreamingHandler     • ToolRegistry             │  │
│  │   • File Analysis       • WebSocket Handler    • HookManager              │  │
│  │   • Event Publishing    • ToolApprovalManager  • HybridOrchestrator       │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌─ HUMAN-IN-THE-LOOP ───────────────────────────────────────────────────────┐  │
│  │                                                                            │  │
│  │  [Checkpoint System]   [Approval Workflow]     [Tool Approval]            │  │
│  │   • State Snapshot      • Timeout Handling     • Manual Mode              │  │
│  │   • Rollback Support    • Escalation Rules     • Approve/Reject           │  │
│  │   • Recovery Points     • Notification System  • Audit Logging            │  │
│  │                                                                            │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Scenario 1: Enterprise Customer Service Automation

### 場景描述

一家中型企業部署 IPA Platform 來自動化客戶服務流程。系統需要處理多種客戶請求類型，並在必要時進行人工審批。

### 涉及功能模組

| 模組 | Phase | 用途 |
|------|-------|------|
| Agent Management | Phase 1 | 創建專業客服Agent |
| GroupChat | Phase 2 | 多Agent協作討論 |
| Handoff | Phase 2 | Agent間任務交接 |
| Session Management | Phase 10-11 | 對話狀態管理 |
| Human-in-the-Loop | Phase 1 | 敏感操作審批 |
| Decision Engine | Phase 7 | 智能路由決策 |

### 完整流程圖

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│              Scenario 1: Enterprise Customer Service Automation                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐                                                                │
│  │   Customer  │                                                                │
│  │   Request   │                                                                │
│  └──────┬──────┘                                                                │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    SESSION MANAGEMENT (Phase 10-11)                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │   │
│  │  │   Create    │  │   Store     │  │   Track     │                      │   │
│  │  │   Session   │──▶   Message   │──▶   Context   │                      │   │
│  │  │   (SSE)     │  │   History   │  │   State     │                      │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                      │   │
│  └──────────────────────────────┬──────────────────────────────────────────┘   │
│                                 │                                               │
│                                 ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     INTENT ANALYSIS (Phase 7)                            │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────┐        │   │
│  │  │                    Decision Engine                           │        │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │        │   │
│  │  │  │   Intent    │  │ Confidence  │  │   Route     │         │        │   │
│  │  │  │ Recognition │──▶  Scoring    │──▶  Decision   │         │        │   │
│  │  │  │             │  │  (0.0-1.0)  │  │             │         │        │   │
│  │  │  └─────────────┘  └─────────────┘  └──────┬──────┘         │        │   │
│  │  └──────────────────────────────────────────┼───────────────────┘        │   │
│  └─────────────────────────────────────────────┼───────────────────────────┘   │
│                                                │                               │
│                    ┌───────────────────────────┼───────────────────────────┐   │
│                    │                           │                           │   │
│                    ▼                           ▼                           ▼   │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │   BILLING INQUIRY    │  │   TECHNICAL SUPPORT  │  │   COMPLAINT HANDLING │ │
│  │    (Simple Query)    │  │    (Complex Issue)   │  │    (Sensitive)       │ │
│  └──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘ │
│             │                         │                         │             │
│             ▼                         ▼                         ▼             │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                      AGENT EXECUTION (Phase 1-2)                        │  │
│  │                                                                          │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │  Billing Agent  │    │  Tech Support   │    │   Complaint     │      │  │
│  │  │                 │    │     Agent       │    │     Agent       │      │  │
│  │  │  • Query DB     │    │  • Diagnose     │    │  • Analyze      │      │  │
│  │  │  • Calculate    │    │  • Troubleshoot │    │  • Prioritize   │      │  │
│  │  │  • Respond      │    │  • Escalate     │    │  • Route        │      │  │
│  │  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘      │  │
│  │           │                      │                      │               │  │
│  └───────────┼──────────────────────┼──────────────────────┼───────────────┘  │
│              │                      │                      │                  │
│              │                      ▼                      │                  │
│              │     ┌────────────────────────────────┐      │                  │
│              │     │    GROUPCHAT (Phase 2)         │      │                  │
│              │     │   Multi-Agent Collaboration    │      │                  │
│              │     │                                │      │                  │
│              │     │  Tech + Billing + Supervisor   │      │                  │
│              │     │  ┌──────────────────────────┐  │      │                  │
│              │     │  │ Turn-based Discussion    │  │      │                  │
│              │     │  │ "Tech: I see billing..."│  │      │                  │
│              │     │  │ "Billing: Confirmed..."  │  │      │                  │
│              │     │  │ "Supervisor: Approved"   │  │      │                  │
│              │     │  └──────────────────────────┘  │      │                  │
│              │     └───────────────┬────────────────┘      │                  │
│              │                     │                       │                  │
│              │                     │                       ▼                  │
│              │                     │      ┌────────────────────────────────┐ │
│              │                     │      │   HANDOFF (Phase 2)            │ │
│              │                     │      │   Policy: GRACEFUL             │ │
│              │                     │      │   Trigger: CAPABILITY_MATCH    │ │
│              │                     │      │                                │ │
│              │                     │      │   Complaint Agent              │ │
│              │                     │      │        ↓ (context preserved)   │ │
│              │                     │      │   Escalation Agent             │ │
│              │                     │      └───────────────┬────────────────┘ │
│              │                     │                      │                  │
│              │                     ▼                      ▼                  │
│              │     ┌─────────────────────────────────────────────────────┐   │
│              │     │          HUMAN-IN-THE-LOOP (Phase 1)                │   │
│              │     │                                                      │   │
│              │     │  ┌─────────────────────────────────────────────┐    │   │
│              │     │  │            Checkpoint System                 │    │   │
│              │     │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │    │   │
│              │     │  │  │ Pending │─▶│ Review  │─▶│ Approved│     │    │   │
│              │     │  │  │ Approval│  │ By Human│  │/Rejected│     │    │   │
│              │     │  │  └─────────┘  └─────────┘  └─────────┘     │    │   │
│              │     │  │                                             │    │   │
│              │     │  │  Triggers:                                  │    │   │
│              │     │  │  • Refund > $100                           │    │   │
│              │     │  │  • Account modification                    │    │   │
│              │     │  │  • Escalation request                      │    │   │
│              │     │  │                                             │    │   │
│              │     │  │  Timeout: 30 min → Auto-escalate           │    │   │
│              │     │  └─────────────────────────────────────────────┘    │   │
│              │     └─────────────────────────┬───────────────────────────┘   │
│              │                               │                               │
│              ▼                               ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        RESPONSE GENERATION                               │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │ │
│  │  │                    LLM Integration (Phase 1)                     │    │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │    │ │
│  │  │  │   Azure    │  │  Response  │  │   Token    │                 │    │ │
│  │  │  │  OpenAI    │──▶  Caching   │──▶  Tracking  │                 │    │ │
│  │  │  │            │  │  (Redis)   │  │            │                 │    │ │
│  │  │  └────────────┘  └────────────┘  └────────────┘                 │    │ │
│  │  └─────────────────────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────┬───────────────────────────┘ │
│                                                │                             │
│                                                ▼                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      SESSION UPDATE (Phase 10-11)                        │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │ │
│  │  │   Store    │  │   Emit     │  │   Update   │  │   Stream   │        │ │
│  │  │  Response  │──▶   Event    │──▶  Metrics   │──▶  to Client │        │ │
│  │  │            │  │ (15 types) │  │            │  │   (SSE)    │        │ │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                │                             │
│                                                ▼                             │
│                                         ┌─────────────┐                      │
│                                         │  Customer   │                      │
│                                         │  Response   │                      │
│                                         └─────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Legend:
═══════
[Phase N] = Feature implemented in that Phase
───▶ = Data/Control flow
┌───┐ = Component/Module
```

### 功能對照表

| 流程步驟 | 使用功能 | 實現位置 |
|----------|----------|----------|
| 創建對話 | SessionService.create() | `domain/sessions/service.py` |
| 意圖識別 | DecisionEngine.analyze() | `domain/orchestration/decision.py` |
| Agent路由 | CapabilityMatcher.match() | `integrations/agent_framework/builders/handoff.py` |
| 多Agent討論 | GroupChatBuilderAdapter | `integrations/agent_framework/builders/groupchat.py` |
| 任務交接 | HandoffBuilderAdapter | `integrations/agent_framework/builders/handoff.py` |
| 人工審批 | CheckpointSystem | `domain/workflows/checkpoints.py` |
| 回應生成 | AgentExecutor.execute() | `domain/sessions/executor.py` |
| 即時串流 | StreamingHandler | `domain/sessions/streaming.py` |

---

## Scenario 2: Intelligent Document Processing Pipeline

### 場景描述

企業需要處理大量文檔（PDF、Excel、Images），自動提取資訊、執行計算分析、並生成結構化報告。

### 涉及功能模組

| 模組 | Phase | 用途 |
|------|-------|------|
| File Analysis | Phase 10 | 文檔類型識別與分析 |
| Code Interpreter | Phase 8 | 執行Python/JS代碼 |
| Concurrent Execution | Phase 2 | 並行處理多文檔 |
| Nested Workflow | Phase 2 | 子流程調用 |
| File Generation | Phase 10 | 報告生成 |

### 完整流程圖

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│             Scenario 2: Intelligent Document Processing Pipeline                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        DOCUMENT UPLOAD                                   │   │
│  │                                                                          │   │
│  │     ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐                  │   │
│  │     │  PDF   │   │ Excel  │   │ Images │   │  Code  │                  │   │
│  │     │ Report │   │  Data  │   │ Scans  │   │ Files  │                  │   │
│  │     └───┬────┘   └───┬────┘   └───┬────┘   └───┬────┘                  │   │
│  │         │            │            │            │                        │   │
│  │         └────────────┴────────────┴────────────┘                        │   │
│  │                              │                                          │   │
│  └──────────────────────────────┼──────────────────────────────────────────┘   │
│                                 │                                               │
│                                 ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    FILE ANALYSIS (Phase 10)                              │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    FileAnalyzer                                  │    │   │
│  │  │                  (Strategy Pattern)                              │    │   │
│  │  │                                                                  │    │   │
│  │  │  file_type = detect(file)                                       │    │   │
│  │  │  analyzer = get_strategy(file_type)                             │    │   │
│  │  │  result = analyzer.analyze(file)                                │    │   │
│  │  │                                                                  │    │   │
│  │  └──────────────────────────┬──────────────────────────────────────┘    │   │
│  │                             │                                           │   │
│  │         ┌───────────────────┼───────────────────┐                      │   │
│  │         ▼                   ▼                   ▼                      │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │   │
│  │  │ Document    │    │   Image     │    │    Code     │                │   │
│  │  │ Analyzer    │    │  Analyzer   │    │  Analyzer   │                │   │
│  │  │             │    │             │    │             │                │   │
│  │  │ • Extract   │    │ • OCR       │    │ • Parse AST │                │   │
│  │  │   text/table│    │ • Object    │    │ • Analyze   │                │   │
│  │  │ • Structure │    │   detection │    │   quality   │                │   │
│  │  │   parsing   │    │ • Caption   │    │ • Find bugs │                │   │
│  │  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                │   │
│  │         │                  │                  │                        │   │
│  └─────────┼──────────────────┼──────────────────┼────────────────────────┘   │
│            │                  │                  │                             │
│            └──────────────────┴──────────────────┘                             │
│                               │                                                │
│                               ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                  CONCURRENT EXECUTION (Phase 2)                          │  │
│  │                                                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                ConcurrentBuilderAdapter                          │    │  │
│  │  │                                                                  │    │  │
│  │  │   ┌──────────┐    ┌──────────┐    ┌──────────┐                  │    │  │
│  │  │   │  Task 1  │    │  Task 2  │    │  Task 3  │                  │    │  │
│  │  │   │ PDF Proc │    │Excel Proc│    │Image Proc│                  │    │  │
│  │  │   └────┬─────┘    └────┬─────┘    └────┬─────┘                  │    │  │
│  │  │        │               │               │                        │    │  │
│  │  │        │    ┌──────────┴──────────┐    │                        │    │  │
│  │  │        │    │   Resource Pool     │    │                        │    │  │
│  │  │        │    │   Max: 5 parallel   │    │                        │    │  │
│  │  │        │    │   Timeout: 300s     │    │                        │    │  │
│  │  │        │    └──────────┬──────────┘    │                        │    │  │
│  │  │        │               │               │                        │    │  │
│  │  │        ▼               ▼               ▼                        │    │  │
│  │  │   ┌──────────┐    ┌──────────┐    ┌──────────┐                  │    │  │
│  │  │   │ Result 1 │    │ Result 2 │    │ Result 3 │                  │    │  │
│  │  │   └──────────┘    └──────────┘    └──────────┘                  │    │  │
│  │  │                                                                  │    │  │
│  │  │   Error Isolation: If Task 2 fails,                             │    │  │
│  │  │   Task 1 & 3 continue independently                             │    │  │
│  │  │                                                                  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └─────────────────────────────────────────────┬───────────────────────────┘  │
│                                                │                              │
│                                                ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    CODE INTERPRETER (Phase 8)                            │ │
│  │                                                                          │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │ │
│  │  │                 CodeInterpreterAdapter                           │    │ │
│  │  │                                                                  │    │ │
│  │  │  ┌────────────────────────────────────────────────────────┐     │    │ │
│  │  │  │                  Sandbox Environment                    │     │    │ │
│  │  │  │                                                         │     │    │ │
│  │  │  │  # Python execution example                            │     │    │ │
│  │  │  │  import pandas as pd                                   │     │    │ │
│  │  │  │  import matplotlib.pyplot as plt                       │     │    │ │
│  │  │  │                                                         │     │    │ │
│  │  │  │  df = pd.read_excel('data.xlsx')                       │     │    │ │
│  │  │  │  summary = df.describe()                               │     │    │ │
│  │  │  │  plt.figure(figsize=(10,6))                            │     │    │ │
│  │  │  │  df['sales'].plot(kind='bar')                          │     │    │ │
│  │  │  │  plt.savefig('chart.png')                              │     │    │ │
│  │  │  │                                                         │     │    │ │
│  │  │  └────────────────────────────────────────────────────────┘     │    │ │
│  │  │                                                                  │    │ │
│  │  │  Security Controls:                                              │    │ │
│  │  │  • No network access                                             │    │ │
│  │  │  • No system calls                                               │    │ │
│  │  │  • Memory limit: 512MB                                           │    │ │
│  │  │  • Timeout: 60s                                                  │    │ │
│  │  │                                                                  │    │ │
│  │  │  Outputs: ┌──────────┐ ┌──────────┐ ┌──────────┐               │    │ │
│  │  │          │  stdout  │ │  files   │ │ visualiz │               │    │ │
│  │  │          │  stderr  │ │ generated│ │  ations  │               │    │ │
│  │  │          └──────────┘ └──────────┘ └──────────┘               │    │ │
│  │  └─────────────────────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────┬───────────────────────────┘ │
│                                                │                             │
│                                                ▼                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    NESTED WORKFLOW (Phase 2)                             │ │
│  │                                                                          │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │ │
│  │  │               NestedWorkflowAdapter                              │    │ │
│  │  │                                                                  │    │ │
│  │  │  Main Workflow: Document Processing                              │    │ │
│  │  │       │                                                          │    │ │
│  │  │       ├──▶ Sub-Workflow 1: Data Validation                      │    │ │
│  │  │       │    └── Validate extracted data against schema           │    │ │
│  │  │       │                                                          │    │ │
│  │  │       ├──▶ Sub-Workflow 2: Enrichment                           │    │ │
│  │  │       │    └── Add metadata, cross-reference                    │    │ │
│  │  │       │                                                          │    │ │
│  │  │       └──▶ Sub-Workflow 3: Quality Check                        │    │ │
│  │  │            └── Verify completeness, accuracy                    │    │ │
│  │  │                                                                  │    │ │
│  │  │  Context Propagation:                                            │    │ │
│  │  │  • Parent context flows to children                             │    │ │
│  │  │  • Child results aggregate to parent                            │    │ │
│  │  │  • Error in child → Parent handles (retry/skip/fail)            │    │ │
│  │  └─────────────────────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────┬───────────────────────────┘ │
│                                                │                             │
│                                                ▼                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    FILE GENERATION (Phase 10)                            │ │
│  │                                                                          │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │ │
│  │  │                    FileGenerator                                 │    │ │
│  │  │                  (Factory Pattern)                               │    │ │
│  │  │                                                                  │    │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │    │ │
│  │  │  │   Report    │  │    Data     │  │    Code     │             │    │ │
│  │  │  │  Generator  │  │  Exporter   │  │  Generator  │             │    │ │
│  │  │  │             │  │             │  │             │             │    │ │
│  │  │  │ • Markdown  │  │ • CSV       │  │ • Python    │             │    │ │
│  │  │  │ • HTML      │  │ • JSON      │  │ • JavaScript│             │    │ │
│  │  │  │ • PDF       │  │ • Excel     │  │ • SQL       │             │    │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘             │    │ │
│  │  │                                                                  │    │ │
│  │  └─────────────────────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                │                             │
│                                                ▼                             │
│                                         ┌─────────────┐                      │
│                                         │  Generated  │                      │
│                                         │   Reports   │                      │
│                                         │   & Data    │                      │
│                                         └─────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 數據流詳圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Document Processing Data Flow                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT                    PROCESSING                         OUTPUT          │
│  ═════                    ══════════                         ══════          │
│                                                                              │
│  ┌──────────┐            ┌──────────────────┐            ┌──────────────┐   │
│  │ PDF      │───────────▶│ DocumentAnalyzer │───────────▶│ Extracted    │   │
│  │ 500 pages│            │ • Table detect   │            │ Text/Tables  │   │
│  └──────────┘            │ • Structure parse│            │ (JSON)       │   │
│                          └──────────────────┘            └──────────────┘   │
│                                    │                            │           │
│  ┌──────────┐            ┌──────────────────┐            ┌──────────────┐   │
│  │ Excel    │───────────▶│ DataAnalyzer     │───────────▶│ Processed    │   │
│  │ 50 sheets│            │ • Schema detect  │            │ DataFrames   │   │
│  └──────────┘            │ • Data transform │            │ (Parquet)    │   │
│                          └──────────────────┘            └──────────────┘   │
│                                    │                            │           │
│  ┌──────────┐            ┌──────────────────┐            ┌──────────────┐   │
│  │ Images   │───────────▶│ ImageAnalyzer    │───────────▶│ OCR Text +   │   │
│  │ 200 files│            │ • OCR extraction │            │ Detections   │   │
│  └──────────┘            │ • Object detect  │            │ (JSON)       │   │
│                          └──────────────────┘            └──────────────┘   │
│                                    │                            │           │
│                                    ▼                            ▼           │
│                          ┌──────────────────────────────────────────┐       │
│                          │            Code Interpreter              │       │
│                          │                                          │       │
│                          │  # Aggregate and analyze                 │       │
│                          │  all_data = merge(pdf, excel, images)    │       │
│                          │  insights = analyze(all_data)            │       │
│                          │  charts = visualize(insights)            │       │
│                          │                                          │       │
│                          └──────────────────────────────────────────┘       │
│                                           │                                 │
│                                           ▼                                 │
│                          ┌──────────────────────────────────────────┐       │
│                          │           Report Generator               │       │
│                          │                                          │       │
│                          │  ┌─────────────┐  ┌─────────────┐       │       │
│                          │  │ Summary.md  │  │ Analysis.html│       │       │
│                          │  │ • Executive │  │ • Interactive│       │       │
│                          │  │   summary   │  │   charts    │       │       │
│                          │  └─────────────┘  └─────────────┘       │       │
│                          │                                          │       │
│                          │  ┌─────────────┐  ┌─────────────┐       │       │
│                          │  │ Data.xlsx   │  │ Raw.json    │       │       │
│                          │  │ • Processed │  │ • All       │       │       │
│                          │  │   tables    │  │   extracted │       │       │
│                          │  └─────────────┘  └─────────────┘       │       │
│                          └──────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Scenario 3: AI-Powered Decision Support System

### 場景描述

企業使用 IPA Platform 構建 AI 決策支援系統，整合外部工具（MCP Servers）和 Claude SDK 進行複雜的分析和建議。

### 涉及功能模組

| 模組 | Phase | 用途 |
|------|-------|------|
| Dynamic Planning | Phase 2 | 任務分解與規劃 |
| MCP Protocol | Phase 9 | 外部工具整合 |
| Claude SDK | Phase 12 | Claude API 整合 |
| Tool Registry | Phase 12 | 工具管理與執行 |
| Hybrid Orchestrator | Phase 12 | 混合編排 |

### 完整流程圖

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│               Scenario 3: AI-Powered Decision Support System                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        USER QUERY                                        │   │
│  │                                                                          │   │
│  │  "Analyze our Q3 sales data and recommend inventory                     │   │
│  │   adjustments based on market trends and competitor analysis"           │   │
│  │                                                                          │   │
│  └────────────────────────────────────┬────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    DYNAMIC PLANNING (Phase 2)                            │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    PlanningAdapter                               │    │   │
│  │  │                  (MagenticBuilder)                               │    │   │
│  │  │                                                                  │    │   │
│  │  │  Step 1: Task Decomposition                                     │    │   │
│  │  │  ┌────────────────────────────────────────────────────────┐     │    │   │
│  │  │  │  Original: "Analyze and recommend"                      │     │    │   │
│  │  │  │                    │                                    │     │    │   │
│  │  │  │                    ▼                                    │     │    │   │
│  │  │  │  ┌──────────────────────────────────────────────────┐  │     │    │   │
│  │  │  │  │  Sub-tasks:                                       │  │     │    │   │
│  │  │  │  │  1. Retrieve Q3 sales data                       │  │     │    │   │
│  │  │  │  │  2. Fetch market trend data                      │  │     │    │   │
│  │  │  │  │  3. Gather competitor information                │  │     │    │   │
│  │  │  │  │  4. Analyze sales performance                    │  │     │    │   │
│  │  │  │  │  5. Generate inventory recommendations           │  │     │    │   │
│  │  │  │  └──────────────────────────────────────────────────┘  │     │    │   │
│  │  │  └────────────────────────────────────────────────────────┘     │    │   │
│  │  │                                                                  │    │   │
│  │  │  Step 2: Dependency Analysis                                    │    │   │
│  │  │  ┌────────────────────────────────────────────────────────┐     │    │   │
│  │  │  │  Task 1 ──┐                                             │     │    │   │
│  │  │  │  Task 2 ──┼──▶ Task 4 ──▶ Task 5                       │     │    │   │
│  │  │  │  Task 3 ──┘                                             │     │    │   │
│  │  │  │  (1,2,3 can run parallel; 4 needs 1,2,3; 5 needs 4)    │     │    │   │
│  │  │  └────────────────────────────────────────────────────────┘     │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    TOOL REGISTRY (Phase 12)                              │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    ToolRegistry                                  │    │   │
│  │  │                                                                  │    │   │
│  │  │  Available Tools:                                                │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  Built-in:                                               │    │    │   │
│  │  │  │  • database_query    - SQL database access              │    │    │   │
│  │  │  │  • file_read         - File system access               │    │    │   │
│  │  │  │  • web_search        - Internet search                  │    │    │   │
│  │  │  │  • calculator        - Mathematical operations          │    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  │  MCP Servers (Phase 9):                                  │    │    │   │
│  │  │  │  • shell_execute     - Command execution                │    │    │   │
│  │  │  │  • filesystem_ops    - Advanced file operations         │    │    │   │
│  │  │  │  • ssh_connect       - Remote server access             │    │    │   │
│  │  │  │  • ldap_query        - Directory service access         │    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  │  Custom:                                                 │    │    │   │
│  │  │  │  • erp_connector     - ERP system integration           │    │    │   │
│  │  │  │  • market_data_api   - External market data             │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  │                                                                  │    │   │
│  │  │  Tool Schema Validation:                                         │    │   │
│  │  │  ✓ Input parameters validated                                    │    │   │
│  │  │  ✓ Output schema enforced                                        │    │   │
│  │  │  ✓ Security permissions checked                                  │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    MCP PROTOCOL (Phase 9)                                │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    MCPServerManager                              │    │   │
│  │  │                                                                  │    │   │
│  │  │  Server Registry:                                                │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  Server ID   │ Status │ Transport │ Tools              │    │    │   │
│  │  │  │─────────────────────────────────────────────────────────│    │    │   │
│  │  │  │  shell       │ Active │ stdio     │ execute, script    │    │    │   │
│  │  │  │  filesystem  │ Active │ stdio     │ read, write, list  │    │    │   │
│  │  │  │  ssh         │ Active │ SSE       │ connect, sftp      │    │    │   │
│  │  │  │  ldap        │ Active │ stdio     │ search, bind       │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  │                                                                  │    │   │
│  │  │  Security Controls:                                              │    │   │
│  │  │  • Command whitelist/blacklist                                   │    │   │
│  │  │  • Path sandbox enforcement                                      │    │   │
│  │  │  • Connection pool limits                                        │    │   │
│  │  │  • TLS/SSL required for sensitive servers                        │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                 HYBRID ORCHESTRATOR (Phase 12)                           │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    HybridOrchestrator                            │    │   │
│  │  │        (Agent Framework + Claude SDK Integration)                │    │   │
│  │  │                                                                  │    │   │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │    │   │
│  │  │  │                  Execution Flow                            │  │    │   │
│  │  │  │                                                            │  │    │   │
│  │  │  │  ┌─────────────────┐      ┌─────────────────┐             │  │    │   │
│  │  │  │  │ Agent Framework │      │   Claude SDK    │             │  │    │   │
│  │  │  │  │                 │      │                 │             │  │    │   │
│  │  │  │  │ • GroupChat     │◄────▶│ • ClaudeClient  │             │  │    │   │
│  │  │  │  │ • Handoff       │      │ • Hooks         │             │  │    │   │
│  │  │  │  │ • Concurrent    │      │ • Streaming     │             │  │    │   │
│  │  │  │  └─────────────────┘      └─────────────────┘             │  │    │   │
│  │  │  │                                                            │  │    │   │
│  │  │  │  Intelligent Routing:                                      │  │    │   │
│  │  │  │  • Simple queries → Claude SDK direct                     │  │    │   │
│  │  │  │  • Complex orchestration → Agent Framework                │  │    │   │
│  │  │  │  • Tool-heavy tasks → Hybrid (both)                       │  │    │   │
│  │  │  └───────────────────────────────────────────────────────────┘  │    │   │
│  │  │                                                                  │    │   │
│  │  │  Hook Pipeline (Phase 12):                                       │    │   │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │    │   │
│  │  │  │  pre_execution → execution → tool_call → post_execution   │  │    │   │
│  │  │  │       │              │            │              │        │  │    │   │
│  │  │  │       ▼              ▼            ▼              ▼        │  │    │   │
│  │  │  │  [logging]     [main LLM]   [approval]     [audit]       │  │    │   │
│  │  │  │  [auth check]   [call]      [if needed]    [metrics]     │  │    │   │
│  │  │  └───────────────────────────────────────────────────────────┘  │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    TOOL APPROVAL (Phase 11)                              │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                 ToolApprovalManager                              │    │   │
│  │  │                                                                  │    │   │
│  │  │  Approval Mode: MANUAL (for sensitive tools)                     │    │   │
│  │  │                                                                  │    │   │
│  │  │  Tool Call Request:                                              │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  Tool: database_query                                    │    │    │   │
│  │  │  │  Query: "SELECT * FROM sales WHERE quarter='Q3'"        │    │    │   │
│  │  │  │  Risk Level: LOW                                         │    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  │  [✓ Auto-Approve]  (risk < threshold)                   │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  │                                                                  │    │   │
│  │  │  Tool Call Request (Sensitive):                                  │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  Tool: erp_connector                                     │    │    │   │
│  │  │  │  Action: "Update inventory levels"                      │    │    │   │
│  │  │  │  Risk Level: HIGH                                        │    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  │  [⏳ Pending Human Approval]                             │    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  │  Approver notified via WebSocket                        │    │    │   │
│  │  │  │  Timeout: 10 minutes                                     │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    DECISION OUTPUT                                       │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │  Analysis Results:                                               │    │   │
│  │  │                                                                  │    │   │
│  │  │  📊 Q3 Sales Performance:                                       │    │   │
│  │  │  • Revenue: $2.5M (+15% YoY)                                    │    │   │
│  │  │  • Top products: A, B, C                                        │    │   │
│  │  │  • Regional breakdown: [chart]                                  │    │   │
│  │  │                                                                  │    │   │
│  │  │  📈 Market Trends:                                              │    │   │
│  │  │  • Industry growth: 8%                                          │    │   │
│  │  │  • Consumer demand shifting to category X                       │    │   │
│  │  │                                                                  │    │   │
│  │  │  🎯 Recommendations:                                            │    │   │
│  │  │  1. Increase inventory for Product A by 20%                    │    │   │
│  │  │  2. Reduce inventory for Product D by 10%                      │    │   │
│  │  │  3. Monitor competitor pricing for Product B                   │    │   │
│  │  │                                                                  │    │   │
│  │  │  Confidence: 85%                                                 │    │   │
│  │  │  Data Sources: ERP, Market API, Competitor DB                   │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Scenario 4: Multi-Agent Research Assistant

### 場景描述

研究團隊使用 IPA Platform 進行多輪對話式研究，多個專業Agent協作收集資訊、分析數據、並生成研究報告。

### 涉及功能模組

| 模組 | Phase | 用途 |
|------|-------|------|
| MultiTurn Conversation | Phase 4 | 多輪對話狀態 |
| Memory Persistence | Phase 4 | 跨對話記憶 |
| GroupChat | Phase 2 | 多Agent討論 |
| Handoff | Phase 2 | 專家切換 |
| Session Management | Phase 10-11 | 對話管理 |

### 完整流程圖

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                 Scenario 4: Multi-Agent Research Assistant                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        RESEARCH SESSION                                  │   │
│  │                                                                          │   │
│  │  User: "I need to research the impact of AI on healthcare,              │   │
│  │         focusing on diagnostic accuracy and patient outcomes"           │   │
│  │                                                                          │   │
│  └────────────────────────────────────┬────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                 MULTITURN ADAPTER (Phase 4)                              │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    MultiTurnAdapter                              │    │   │
│  │  │                 (CheckpointStorage)                              │    │   │
│  │  │                                                                  │    │   │
│  │  │  Conversation State Management:                                  │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  Turn 1: Initial research request                        │    │    │   │
│  │  │  │  Turn 2: Clarification (scope: diagnostic AI)            │    │    │   │
│  │  │  │  Turn 3: Literature review results                       │    │    │   │
│  │  │  │  Turn 4: Statistical analysis request                    │    │    │   │
│  │  │  │  Turn 5: Expert opinion consultation                     │    │    │   │
│  │  │  │  ...                                                      │    │    │   │
│  │  │  │  Turn N: Final report generation                         │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  │                                                                  │    │   │
│  │  │  Checkpoint Storage:                                             │    │   │
│  │  │  • State snapshot after each turn                               │    │   │
│  │  │  • Rollback capability to any previous state                    │    │   │
│  │  │  • Context window optimization                                   │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                 MEMORY PERSISTENCE (Phase 4)                             │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                    MemoryStorage                                 │    │   │
│  │  │                                                                  │    │   │
│  │  │  Short-term Memory (Session):                                    │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  • Current research topic: AI in Healthcare             │    │    │   │
│  │  │  │  • Focus areas: Diagnostics, Patient Outcomes           │    │    │   │
│  │  │  │  • Collected papers: 15                                  │    │    │   │
│  │  │  │  • Key findings: [list]                                  │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  │                                                                  │    │   │
│  │  │  Long-term Memory (Persistent):                                  │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  • User preferences: Prefers statistical evidence       │    │    │   │
│  │  │  │  • Previous research: Oncology, Cardiology              │    │    │   │
│  │  │  │  • Trusted sources: PubMed, Nature, JAMA                │    │    │   │
│  │  │  │  • Citation format: APA                                  │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  │                                                                  │    │   │
│  │  │  Storage Backend:                                                │    │   │
│  │  │  • Redis: Session memory (TTL: 2 hours)                         │    │   │
│  │  │  • PostgreSQL: Long-term memory (persistent)                    │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    GROUPCHAT (Phase 2)                                   │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │              GroupChatBuilderAdapter                             │    │   │
│  │  │                                                                  │    │   │
│  │  │  Research Team Configuration:                                    │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │    │   │
│  │  │  │  │  Literature  │  │  Statistics  │  │   Medical    │  │    │    │   │
│  │  │  │  │    Agent     │  │    Agent     │  │   Expert     │  │    │    │   │
│  │  │  │  │              │  │              │  │              │  │    │    │   │
│  │  │  │  │ • PubMed     │  │ • Data       │  │ • Clinical   │  │    │    │   │
│  │  │  │  │   search     │  │   analysis   │  │   context    │  │    │    │   │
│  │  │  │  │ • Citation   │  │ • Hypothesis │  │ • Validity   │  │    │    │   │
│  │  │  │  │   management │  │   testing    │  │   check      │  │    │    │   │
│  │  │  │  └──────────────┘  └──────────────┘  └──────────────┘  │    │    │   │
│  │  │  │              │              │              │            │    │    │   │
│  │  │  │              └──────────────┴──────────────┘            │    │    │   │
│  │  │  │                         │                               │    │    │   │
│  │  │  │                         ▼                               │    │    │   │
│  │  │  │            ┌──────────────────────────┐                 │    │    │   │
│  │  │  │            │     Coordinator Agent    │                 │    │    │   │
│  │  │  │            │   (Turn Management)      │                 │    │    │   │
│  │  │  │            └──────────────────────────┘                 │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  │                                                                  │    │   │
│  │  │  Collaboration Flow:                                             │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │  1. Coordinator: "Let's start with literature review"   │    │    │   │
│  │  │  │  2. Literature: "Found 50 papers on AI diagnostics"     │    │    │   │
│  │  │  │  3. Statistics: "Key metric: sensitivity 95%, spec 89%" │    │    │   │
│  │  │  │  4. Medical: "These results align with clinical trials" │    │    │   │
│  │  │  │  5. Coordinator: "Let's focus on radiology subset"      │    │    │   │
│  │  │  │  ...                                                     │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    HANDOFF (Phase 2)                                     │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                  HandoffBuilderAdapter                           │    │   │
│  │  │                                                                  │    │   │
│  │  │  Handoff Scenario: Specialized Analysis Needed                   │    │   │
│  │  │                                                                  │    │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  │    Statistics Agent                                      │    │    │   │
│  │  │  │         │                                                │    │    │   │
│  │  │  │         │ Trigger: CAPABILITY_MATCH                     │    │    │   │
│  │  │  │         │ Reason: "Meta-analysis required"              │    │    │   │
│  │  │  │         │                                                │    │    │   │
│  │  │  │         ▼                                                │    │    │   │
│  │  │  │    ┌─────────────────────────────────────┐              │    │    │   │
│  │  │  │    │        Context Transfer             │              │    │    │   │
│  │  │  │    │  • Current findings                 │              │    │    │   │
│  │  │  │    │  • Data collected                   │              │    │    │   │
│  │  │  │    │  • Research objectives              │              │    │    │   │
│  │  │  │    └─────────────────────────────────────┘              │    │    │   │
│  │  │  │         │                                                │    │    │   │
│  │  │  │         │ Policy: GRACEFUL                              │    │    │   │
│  │  │  │         │ (Complete current subtask first)              │    │    │   │
│  │  │  │         │                                                │    │    │   │
│  │  │  │         ▼                                                │    │    │   │
│  │  │  │    Meta-Analysis Specialist Agent                       │    │    │   │
│  │  │  │    • Random effects model                               │    │    │   │
│  │  │  │    • Heterogeneity analysis                             │    │    │   │
│  │  │  │    • Publication bias check                             │    │    │   │
│  │  │  │                                                          │    │    │   │
│  │  │  └─────────────────────────────────────────────────────────┘    │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                 RESEARCH OUTPUT                                          │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │                                                                  │    │   │
│  │  │  📚 Literature Summary:                                         │    │   │
│  │  │  • 50 papers reviewed, 15 highly relevant                       │    │   │
│  │  │  • Key themes: CNN-based diagnosis, NLP for records            │    │   │
│  │  │                                                                  │    │   │
│  │  │  📊 Statistical Analysis:                                       │    │   │
│  │  │  • Meta-analysis: pooled sensitivity 94.2% (95% CI: 92-96%)   │    │   │
│  │  │  • Heterogeneity: I² = 45% (moderate)                          │    │   │
│  │  │  • Publication bias: Egger test p=0.12 (no significant bias)  │    │   │
│  │  │                                                                  │    │   │
│  │  │  🏥 Clinical Implications:                                      │    │   │
│  │  │  • AI diagnostic tools show promise in radiology               │    │   │
│  │  │  • Human oversight remains essential                           │    │   │
│  │  │  • Implementation challenges: data quality, integration        │    │   │
│  │  │                                                                  │    │   │
│  │  │  📝 Generated Report:                                           │    │   │
│  │  │  • Full research report (PDF, 25 pages)                        │    │   │
│  │  │  • Executive summary (1 page)                                   │    │   │
│  │  │  • Data appendix (Excel)                                        │    │   │
│  │  │  • Bibliography (APA format, 50 citations)                     │    │   │
│  │  │                                                                  │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Feature Module Relationship

### 模組依賴關係圖

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       Feature Module Dependency Graph                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                              ┌─────────────────┐                                │
│                              │   Frontend UI   │                                │
│                              │   (React 18)    │                                │
│                              └────────┬────────┘                                │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                          API Layer (FastAPI)                             │   │
│  │                                                                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│  │  │ /agents  │ │/workflows│ │/executions│ │/sessions │ │/claude_sdk│      │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │   │
│  │       │            │            │            │            │             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│  │  │/groupchat│ │ /handoff │ │/concurrent│ │ /nested  │ │ /planning│      │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │   │
│  │       │            │            │            │            │             │   │
│  └───────┴────────────┴────────────┴────────────┴────────────┴─────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Integration Layer                                   │   │
│  │                                                                          │   │
│  │  ┌───────────────────────────┐    ┌───────────────────────────┐        │   │
│  │  │  Microsoft Agent Framework │    │      Claude Agent SDK     │        │   │
│  │  │                            │    │                           │        │   │
│  │  │  ┌─────────────────────┐  │    │  ┌─────────────────────┐  │        │   │
│  │  │  │ GroupChatBuilder    │──┼────┼─▶│ ClaudeSDKClient    │  │        │   │
│  │  │  │ Adapter             │  │    │  │                     │  │        │   │
│  │  │  └─────────────────────┘  │    │  └─────────────────────┘  │        │   │
│  │  │           │               │    │           │               │        │   │
│  │  │  ┌─────────────────────┐  │    │  ┌─────────────────────┐  │        │   │
│  │  │  │ HandoffBuilder      │──┼────┼─▶│ ToolRegistry       │  │        │   │
│  │  │  │ Adapter             │  │    │  │                     │  │        │   │
│  │  │  └─────────────────────┘  │    │  └─────────────────────┘  │        │   │
│  │  │           │               │    │           │               │        │   │
│  │  │  ┌─────────────────────┐  │    │  ┌─────────────────────┐  │        │   │
│  │  │  │ ConcurrentBuilder   │──┼────┼─▶│ HookManager        │  │        │   │
│  │  │  │ Adapter             │  │    │  │                     │  │        │   │
│  │  │  └─────────────────────┘  │    │  └─────────────────────┘  │        │   │
│  │  │           │               │    │           │               │        │   │
│  │  │  ┌─────────────────────┐  │    │  ┌─────────────────────┐  │        │   │
│  │  │  │ MultiTurnAdapter    │──┼────┼─▶│ HybridOrchestrator │  │        │   │
│  │  │  │                     │  │    │  │                     │  │        │   │
│  │  │  └─────────────────────┘  │    │  └─────────────────────┘  │        │   │
│  │  │                            │    │                           │        │   │
│  │  └───────────────┬────────────┘    └─────────────┬─────────────┘        │   │
│  │                  │                               │                       │   │
│  │                  └───────────────┬───────────────┘                       │   │
│  │                                  │                                       │   │
│  │                                  ▼                                       │   │
│  │               ┌───────────────────────────────────┐                     │   │
│  │               │           MCP Protocol            │                     │   │
│  │               │                                   │                     │   │
│  │               │  ┌─────────┐ ┌─────────┐        │                     │   │
│  │               │  │  Shell  │ │Filesystem│        │                     │   │
│  │               │  │  Server │ │  Server │        │                     │   │
│  │               │  └─────────┘ └─────────┘        │                     │   │
│  │               │  ┌─────────┐ ┌─────────┐        │                     │   │
│  │               │  │   SSH   │ │  LDAP   │        │                     │   │
│  │               │  │  Server │ │  Server │        │                     │   │
│  │               │  └─────────┘ └─────────┘        │                     │   │
│  │               └───────────────────────────────────┘                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        Domain Layer                                      │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │   │
│  │  │    Agent     │  │   Workflow   │  │  Execution   │                  │   │
│  │  │   Service    │◀─▶   Service    │◀─▶   Service    │                  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                  │   │
│  │         │                 │                 │                           │   │
│  │         │                 ▼                 │                           │   │
│  │         │         ┌──────────────┐         │                           │   │
│  │         └────────▶│   Session    │◀────────┘                           │   │
│  │                   │   Service    │                                      │   │
│  │                   └──────────────┘                                      │   │
│  │                          │                                              │   │
│  │  ┌──────────────┐        │        ┌──────────────┐                     │   │
│  │  │    State     │◀───────┼───────▶│  Checkpoint  │                     │   │
│  │  │   Machine    │        │        │    System    │                     │   │
│  │  └──────────────┘        │        └──────────────┘                     │   │
│  │                          │                                              │   │
│  │  ┌──────────────┐        │        ┌──────────────┐                     │   │
│  │  │   Decision   │◀───────┴───────▶│    File      │                     │   │
│  │  │    Engine    │                 │   Analyzer   │                     │   │
│  │  └──────────────┘                 └──────────────┘                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     Infrastructure Layer                                 │   │
│  │                                                                          │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │   │
│  │  │    PostgreSQL    │  │      Redis       │  │    RabbitMQ      │      │   │
│  │  │                  │  │                  │  │                  │      │   │
│  │  │  • Persistence   │  │  • Caching       │  │  • Messaging     │      │   │
│  │  │  • Transactions  │  │  • Sessions      │  │  • Event Queue   │      │   │
│  │  │  • Migrations    │  │  • Rate Limiting │  │  • Pub/Sub       │      │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘      │   │
│  │                                                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │   │
│  │  │                       Azure OpenAI                               │   │   │
│  │  │  • LLM Inference  • Response Caching  • Token Tracking          │   │   │
│  │  └──────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

Legend:
═══════
───▶  : Direct dependency (uses)
◀──▶  : Bidirectional communication
┌───┐ : Module/Component
```

---

## 6. Complete Data Flow

### 完整請求處理流程

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Complete Request Data Flow                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────┐                                                                   │
│  │  Client  │                                                                   │
│  │ (Browser)│                                                                   │
│  └────┬─────┘                                                                   │
│       │ HTTP/WebSocket Request                                                  │
│       ▼                                                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │ 1. API GATEWAY                                                          │    │
│  │    ┌──────────────────────────────────────────────────────────────┐    │    │
│  │    │  FastAPI Router                                               │    │    │
│  │    │  • Authentication (JWT/API Key)                              │    │    │
│  │    │  • Rate Limiting (Redis)                                      │    │    │
│  │    │  • Request Validation (Pydantic)                             │    │    │
│  │    │  • CORS Handling                                              │    │    │
│  │    └──────────────────────────────────────────────────────────────┘    │    │
│  └────────────────────────────────────┬───────────────────────────────────┘    │
│                                       │                                         │
│                                       ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │ 2. SESSION MANAGEMENT                                                   │    │
│  │    ┌──────────────────────────────────────────────────────────────┐    │    │
│  │    │  SessionService                                               │    │    │
│  │    │  • Create/Resume Session                                      │    │    │
│  │    │  • Message History Loading                                    │    │    │
│  │    │  • Context Assembly                                           │    │    │
│  │    │                                                               │    │    │
│  │    │  SessionEventPublisher                                        │    │    │
│  │    │  • Emit: SESSION_CREATED, MESSAGE_ADDED, ...                 │    │    │
│  │    └──────────────────────────────────────────────────────────────┘    │    │
│  └────────────────────────────────────┬───────────────────────────────────┘    │
│                                       │                                         │
│                                       ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │ 3. ORCHESTRATION ROUTING                                                │    │
│  │    ┌──────────────────────────────────────────────────────────────┐    │    │
│  │    │  HybridOrchestrator (Phase 12)                                │    │    │
│  │    │                                                               │    │    │
│  │    │  Route Decision:                                              │    │    │
│  │    │  ┌─────────────────────────────────────────────────────┐     │    │    │
│  │    │  │  IF simple_query AND no_tools_needed:              │     │    │    │
│  │    │  │      → Claude SDK Direct                            │     │    │    │
│  │    │  │  ELIF multi_agent_required:                         │     │    │    │
│  │    │  │      → Agent Framework (GroupChat/Handoff)          │     │    │    │
│  │    │  │  ELIF tool_heavy_task:                              │     │    │    │
│  │    │  │      → Hybrid (Both frameworks)                     │     │    │    │
│  │    │  │  ELSE:                                               │     │    │    │
│  │    │  │      → Agent Framework Default                      │     │    │    │
│  │    │  └─────────────────────────────────────────────────────┘     │    │    │
│  │    └──────────────────────────────────────────────────────────────┘    │    │
│  └────────────────────────────────────┬───────────────────────────────────┘    │
│                                       │                                         │
│               ┌───────────────────────┼───────────────────────┐                │
│               ▼                       ▼                       ▼                │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐       │
│  │ 4A. CLAUDE SDK     │  │ 4B. AGENT FRAMEWORK│  │ 4C. HYBRID PATH    │       │
│  │                    │  │                    │  │                    │       │
│  │ ClaudeSDKClient    │  │ GroupChatAdapter   │  │ Both frameworks    │       │
│  │ • Query API        │  │ HandoffAdapter     │  │ coordinated        │       │
│  │ • Streaming        │  │ ConcurrentAdapter  │  │                    │       │
│  │ • Hooks            │  │ MultiTurnAdapter   │  │                    │       │
│  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘       │
│            │                       │                       │                   │
│            └───────────────────────┼───────────────────────┘                   │
│                                    │                                           │
│                                    ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │ 5. TOOL EXECUTION                                                       │   │
│  │    ┌──────────────────────────────────────────────────────────────┐    │   │
│  │    │  ToolRegistry + MCP Servers                                   │    │   │
│  │    │                                                               │    │   │
│  │    │  Tool Call Flow:                                              │    │   │
│  │    │  ┌─────────────────────────────────────────────────────┐     │    │   │
│  │    │  │  1. Tool requested by LLM                           │     │    │   │
│  │    │  │  2. Schema validation (ToolRegistry)                │     │    │   │
│  │    │  │  3. Approval check (ToolApprovalManager)            │     │    │   │
│  │    │  │     • Auto-approve if risk < threshold              │     │    │   │
│  │    │  │     • Human approval if sensitive                   │     │    │   │
│  │    │  │  4. Execute tool (MCP Server / Built-in)            │     │    │   │
│  │    │  │  5. Return result to LLM                            │     │    │   │
│  │    │  └─────────────────────────────────────────────────────┘     │    │   │
│  │    └──────────────────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────┬───────────────────────────────────┘   │
│                                       │                                        │
│                                       ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │ 6. LLM INFERENCE                                                        │   │
│  │    ┌──────────────────────────────────────────────────────────────┐    │   │
│  │    │  Azure OpenAI Integration                                     │    │   │
│  │    │                                                               │    │   │
│  │    │  ┌─────────────────────────────────────────────────────┐     │    │   │
│  │    │  │  Request:                                            │     │    │   │
│  │    │  │  • Model: gpt-4 / gpt-4-turbo                       │     │    │   │
│  │    │  │  • Messages: [system, user, assistant, tool_result] │     │    │   │
│  │    │  │  • Tools: [available_tools_schema]                  │     │    │   │
│  │    │  │  • Temperature: 0.7                                  │     │    │   │
│  │    │  └─────────────────────────────────────────────────────┘     │    │   │
│  │    │                                                               │    │   │
│  │    │  Caching (Redis):                                             │    │   │
│  │    │  • Cache key: hash(model + messages)                         │    │   │
│  │    │  • TTL: 1 hour                                                │    │   │
│  │    │  • Cache hit → Skip API call                                  │    │   │
│  │    │                                                               │    │   │
│  │    │  Token Tracking:                                              │    │   │
│  │    │  • Input tokens, Output tokens, Total cost                   │    │   │
│  │    └──────────────────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────┬───────────────────────────────────┘   │
│                                       │                                        │
│                                       ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │ 7. RESPONSE STREAMING                                                   │   │
│  │    ┌──────────────────────────────────────────────────────────────┐    │   │
│  │    │  StreamingHandler                                             │    │   │
│  │    │                                                               │    │   │
│  │    │  SSE (Server-Sent Events):                                    │    │   │
│  │    │  ┌─────────────────────────────────────────────────────┐     │    │   │
│  │    │  │  event: message_start                                │     │    │   │
│  │    │  │  data: {"type": "text", "content": ""}              │     │    │   │
│  │    │  │                                                      │     │    │   │
│  │    │  │  event: content_delta                                │     │    │   │
│  │    │  │  data: {"delta": "Here is my analysis..."}          │     │    │   │
│  │    │  │                                                      │     │    │   │
│  │    │  │  event: tool_call                                    │     │    │   │
│  │    │  │  data: {"tool": "database_query", "status": "..."}  │     │    │   │
│  │    │  │                                                      │     │    │   │
│  │    │  │  event: message_end                                  │     │    │   │
│  │    │  │  data: {"total_tokens": 1500}                       │     │    │   │
│  │    │  └─────────────────────────────────────────────────────┘     │    │   │
│  │    └──────────────────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────┬───────────────────────────────────┘   │
│                                       │                                        │
│                                       ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │ 8. PERSISTENCE & EVENTS                                                 │   │
│  │    ┌──────────────────────────────────────────────────────────────┐    │   │
│  │    │  Data Persistence:                                            │    │   │
│  │    │  • PostgreSQL: Session, Messages, ToolCalls                  │    │   │
│  │    │  • Redis: Session cache (TTL: 2h), Message cache (TTL: 1h)   │    │   │
│  │    │                                                               │    │   │
│  │    │  Event Publishing:                                            │    │   │
│  │    │  • SESSION_UPDATED                                            │    │   │
│  │    │  • MESSAGE_COMPLETED                                          │    │   │
│  │    │  • TOOL_CALL_EXECUTED                                         │    │   │
│  │    │  • EXECUTION_COMPLETED                                        │    │   │
│  │    │                                                               │    │   │
│  │    │  Metrics:                                                     │    │   │
│  │    │  • Response time, Token usage, Tool call count               │    │   │
│  │    └──────────────────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────┬───────────────────────────────────┘   │
│                                       │                                        │
│                                       ▼                                        │
│                                  ┌──────────┐                                  │
│                                  │  Client  │                                  │
│                                  │ Response │                                  │
│                                  └──────────┘                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: Feature to Phase Mapping

| Feature | Phase(s) | Key Files |
|---------|----------|-----------|
| Agent CRUD | 1 | `domain/agents/service.py` |
| Workflow Engine | 1-2 | `domain/workflows/service.py` |
| Execution State Machine | 1 | `domain/executions/state_machine.py` |
| GroupChat | 2, 3 | `integrations/agent_framework/builders/groupchat.py` |
| Handoff | 2, 3 | `integrations/agent_framework/builders/handoff.py` |
| Concurrent Execution | 2, 3 | `integrations/agent_framework/builders/concurrent.py` |
| Dynamic Planning | 2, 4 | `integrations/agent_framework/builders/planning.py` |
| Nested Workflows | 2, 4 | `integrations/agent_framework/builders/nested_workflow.py` |
| MultiTurn Conversation | 4 | `integrations/agent_framework/multiturn/adapter.py` |
| Human-in-the-Loop | 1 | `domain/workflows/checkpoints.py` |
| Decision Engine | 7 | `domain/orchestration/decision.py` |
| Code Interpreter | 8 | `integrations/agent_framework/builders/code_interpreter.py` |
| MCP Protocol | 9 | `integrations/mcp/core/` |
| MCP Servers | 9 | `integrations/mcp/servers/` |
| Session Management | 10-11 | `domain/sessions/` |
| Agent Executor | 11 | `domain/sessions/executor.py` |
| Streaming Handler | 11 | `domain/sessions/streaming.py` |
| Claude SDK Client | 12 | `integrations/claude_sdk/client.py` |
| Tool Registry | 12 | `integrations/claude_sdk/tools/registry.py` |
| Hook Manager | 12 | `integrations/claude_sdk/hooks/manager.py` |
| Hybrid Orchestrator | 12 | `integrations/claude_sdk/hybrid/orchestrator.py` |

---

**Generated**: 2025-12-29
