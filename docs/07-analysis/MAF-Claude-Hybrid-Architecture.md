# 企業 IT 事件智能處理平台：MAF + Claude Agent SDK 混合架構實現

> **文件版本**: 1.1
> **最後更新**: 2026-01-13
> **場景**: APAC 區域 IT 運維自動化平台
> **狀態**: 🟢 核心架構已實現 (Phase 12-20)

---

## 實現狀態總覽

> **重要說明**: 本文件描述的混合架構設計已在 Phase 12-20 中完成核心實現。Phase 7-11 原計劃的 AI 自主能力已由 Claude Agent SDK 替代實現，無需重複開發。

### 組件實現狀態

| 層級 | 組件 | 狀態 | 實現位置 |
|------|------|------|---------|
| **Layer 3: MAF 編排層** | Orchestrator Agent | ✅ 已實現 | `integrations/agent_framework/builders/` |
| | Intent Router | ✅ 已實現 | `integrations/hybrid/intent/` |
| | Risk Assessor | ✅ 已實現 | `integrations/hybrid/risk/` |
| | HITL Manager | ✅ 已實現 | `integrations/ag_ui/features/human_in_loop.py` |
| | Workflow Engine | ✅ 已實現 | 11 個 Builder 適配器 |
| **Layer 4: Claude Worker** | ClaudeSDKClient | ✅ 已實現 | `integrations/claude_sdk/client.py` |
| | Autonomous Executor | ✅ 已實現 | `integrations/claude_sdk/autonomous/` |
| | Hook System | ✅ 已實現 | `integrations/claude_sdk/hooks/` |
| | Worker Pool (容器化) | 📋 Phase 21 | 計劃中 |
| **Layer 5: MCP 工具層** | MCP Gateway | ✅ 已實現 | `integrations/mcp/` |
| | Tool Registry | ✅ 已實現 | `integrations/claude_sdk/tools/registry.py` |

### 版本演進說明

```
V1 原計劃 (Phase 1-11): MAF 基礎 + AI 自主能力
    ↓
    Phase 7-11 (AI 自主) 已由 Phase 12-15 (Claude SDK) 替代實現
    ↓
V2 實際路線 (Phase 12-20): Claude SDK 整合 + 前端 UX ← 當前狀態
    ↓
V3 計劃中 (Phase 21-23): 沙箱安全 + 自主學習 + 多 Agent 協調
```

### Phase 7-11 功能對照

| V1 功能 (Phase 7-11) | V2 替代實現 (Phase 12-15) | 狀態 |
|---------------------|-------------------------|------|
| LLM 服務整合 (Phase 7) | ClaudeSDKClient | ✅ 已覆蓋 |
| Code Interpreter (Phase 8) | CodeInterpreterAdapter | ✅ 已覆蓋 |
| MCP Architecture (Phase 9) | Claude MCP Integration | ✅ 已覆蓋 |
| Session Mode (Phase 10) | Claude Session API | ✅ 已覆蓋 |
| Agent-Session (Phase 11) | HybridEventBridge | ✅ 已覆蓋 |

---

## 執行摘要

本文件以「**企業 IT 事件智能處理平台**」為場景，詳細說明 Microsoft Agent Framework (MAF) 與 Claude Agent SDK 的混合架構實現。該平台處理來自 ServiceNow、用戶報告、系統監控的各類 IT 事件，通過智能編排和自主執行實現端到端的自動化處理。

### 架構核心原則

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   MAF Orchestrator                Claude Worker Service                  │
│   ════════════════                ═════════════════════                  │
│                                                                          │
│   「指揮官」                       「執行者」                             │
│   ─────────                       ─────────                             │
│   • 決定做什麼                     • 決定怎麼做                          │
│   • 決定誰來做                     • 自主規劃執行步驟                    │
│   • 決定何時需要人工               • 使用工具完成任務                    │
│   • 記錄和審計                     • 驗證執行結果                        │
│                                                                          │
│                    統一 MCP 工具層                                       │
│                    ════════════════                                      │
│                    • 單一工具定義                                        │
│                    • 統一權限策略                                        │
│                    • 集中審計日誌                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 場景概述

### 1.1 業務背景

**APAC Glider IT 運維平台**需要處理來自 8 個國家/地區的 IT 服務請求：

| 來源 | 類型 | 日均量 |
|------|------|--------|
| ServiceNow | 事件工單 | ~500 |
| 用戶報告 | Teams/Email | ~200 |
| 系統監控 | Prometheus/Grafana 告警 | ~1000 |
| 安全系統 | Microsoft Defender 告警 | ~100 |

### 1.2 處理類型

| 類型 | 複雜度 | 自動化率目標 |
|------|--------|-------------|
| 密碼重設 | 低 | 95% |
| 權限申請 | 中 | 80% |
| 系統故障排查 | 高 | 60% |
| 安全事件響應 | 關鍵 | 40% |
| 數據管道修復 | 高 | 50% |

### 1.3 複雜場景示例

本文件將以以下**複雜場景**為例，展示完整架構：

> **場景**：用戶報告「APAC Glider ETL Pipeline 失敗，導致日報表無法生成」
>
> 這個場景涉及：
> - 多系統診斷（ServiceNow、Azure Data Factory、SQL Server、SharePoint）
> - 多 Agent 協作（診斷、修復、驗證、通知）
> - 人工審批（生產環境變更）
> - 審計追蹤（合規要求）

---

## 2. 完整架構設計

### 2.1 整體架構圖

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           企業 IT 事件智能處理平台                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ╔═══════════════════════════════════════════════════════════════════════════════╗  │
│  ║                              入口層                                            ║  │
│  ╠═══════════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                                ║  │
│  ║   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          ║  │
│  ║   │ ServiceNow  │  │   Teams     │  │ Prometheus  │  │  Defender   │          ║  │
│  ║   │  Webhook    │  │    Bot      │  │   Alert     │  │   Alert     │          ║  │
│  ║   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          ║  │
│  ║          │                │                │                │                  ║  │
│  ║          └────────────────┴────────────────┴────────────────┘                  ║  │
│  ║                                    │                                           ║  │
│  ║                                    ▼                                           ║  │
│  ║                    ┌───────────────────────────────┐                           ║  │
│  ║                    │      Event Ingestion API      │                           ║  │
│  ║                    │    (FastAPI + Redis Queue)    │                           ║  │
│  ║                    └───────────────┬───────────────┘                           ║  │
│  ╚════════════════════════════════════│═══════════════════════════════════════════╝  │
│                                       │                                              │
│  ╔════════════════════════════════════│═══════════════════════════════════════════╗  │
│  ║                              MAF 編排層                                        ║  │
│  ╠════════════════════════════════════│═══════════════════════════════════════════╣  │
│  ║                                    ▼                                           ║  │
│  ║   ┌────────────────────────────────────────────────────────────────────────┐   ║  │
│  ║   │                     MAF Orchestrator Service                           │   ║  │
│  ║   │                   (使用 Claude Sonnet 作為 LLM)                         │   ║  │
│  ║   │                                                                        │   ║  │
│  ║   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │   ║  │
│  ║   │   │Intent Router │  │ Risk Assessor│  │ HITL Manager │                │   ║  │
│  ║   │   │(意圖識別)    │  │ (風險評估)   │  │ (人機協作)   │                │   ║  │
│  ║   │   └──────────────┘  └──────────────┘  └──────────────┘                │   ║  │
│  ║   │                                                                        │   ║  │
│  ║   │   ┌────────────────────────────────────────────────────────────────┐  │   ║  │
│  ║   │   │                    Workflow Engine                             │  │   ║  │
│  ║   │   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │  │   ║  │
│  ║   │   │  │Sequential│  │ Handoff │  │GroupChat│  │Magentic │           │  │   ║  │
│  ║   │   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘           │  │   ║  │
│  ║   │   └────────────────────────────────────────────────────────────────┘  │   ║  │
│  ║   │                                                                        │   ║  │
│  ║   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │   ║  │
│  ║   │   │ Checkpoint   │  │ Audit Logger │  │ AG-UI Server │                │   ║  │
│  ║   │   │ (Cosmos DB)  │  │ (Azure Mon.) │  │ (SSE Stream) │                │   ║  │
│  ║   │   └──────────────┘  └──────────────┘  └──────────────┘                │   ║  │
│  ║   └────────────────────────────────────────────────────────────────────────┘   ║  │
│  ║                                    │                                           ║  │
│  ║                    ┌───────────────┴───────────────┐                           ║  │
│  ║                    │      Task Dispatcher          │                           ║  │
│  ║                    │   (任務分發到 Worker Pool)    │                           ║  │
│  ║                    └───────────────┬───────────────┘                           ║  │
│  ╚════════════════════════════════════│═══════════════════════════════════════════╝  │
│                                       │                                              │
│  ╔════════════════════════════════════│═══════════════════════════════════════════╗  │
│  ║                          Claude Worker 執行層                                  ║  │
│  ╠════════════════════════════════════│═══════════════════════════════════════════╣  │
│  ║                                    ▼                                           ║  │
│  ║   ┌─────────────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │                        Worker Pool (Kubernetes)                         │  ║  │
│  ║   │                                                                         │  ║  │
│  ║   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │  ║  │
│  ║   │  │ Diagnostic      │  │ Remediation     │  │ Verification    │         │  ║  │
│  ║   │  │ Worker          │  │ Worker          │  │ Worker          │         │  ║  │
│  ║   │  │ (Claude Sonnet) │  │ (Claude Sonnet) │  │ (Claude Haiku)  │         │  ║  │
│  ║   │  │                 │  │                 │  │                 │         │  ║  │
│  ║   │  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │         │  ║  │
│  ║   │  │ │Claude Agent │ │  │ │Claude Agent │ │  │ │Claude Agent │ │         │  ║  │
│  ║   │  │ │    SDK      │ │  │ │    SDK      │ │  │ │    SDK      │ │         │  ║  │
│  ║   │  │ │             │ │  │ │             │ │  │ │             │ │         │  ║  │
│  ║   │  │ │• Agentic    │ │  │ │• Agentic    │ │  │ │• Agentic    │ │         │  ║  │
│  ║   │  │ │  Loop       │ │  │ │  Loop       │ │  │ │  Loop       │ │         │  ║  │
│  ║   │  │ │• Extended   │ │  │ │• Extended   │ │  │ │• Fast       │ │         │  ║  │
│  ║   │  │ │  Thinking   │ │  │ │  Thinking   │ │  │ │  Validation │ │         │  ║  │
│  ║   │  │ │• SubAgents  │ │  │ │• SubAgents  │ │  │ │             │ │         │  ║  │
│  ║   │  │ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │         │  ║  │
│  ║   │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │  ║  │
│  ║   │           │                    │                    │                   │  ║  │
│  ║   └───────────┴────────────────────┴────────────────────┴───────────────────┘  ║  │
│  ║                                    │                                           ║  │
│  ╚════════════════════════════════════│═══════════════════════════════════════════╝  │
│                                       │                                              │
│  ╔════════════════════════════════════│═══════════════════════════════════════════╗  │
│  ║                           統一 MCP 工具層                                      ║  │
│  ╠════════════════════════════════════│═══════════════════════════════════════════╣  │
│  ║                                    ▼                                           ║  │
│  ║   ┌─────────────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │                         MCP Gateway Service                             │  ║  │
│  ║   │                    (統一工具存取 + 權限控制 + 審計)                      │  ║  │
│  ║   │                                                                         │  ║  │
│  ║   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  ║  │
│  ║   │   │ Permission  │  │   Rate      │  │   Audit     │  │  Circuit    │   │  ║  │
│  ║   │   │  Manager    │  │  Limiter    │  │   Logger    │  │  Breaker    │   │  ║  │
│  ║   │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  ║  │
│  ║   └─────────────────────────────────────────────────────────────────────────┘  ║  │
│  ║                                    │                                           ║  │
│  ║          ┌─────────────────────────┼─────────────────────────┐                ║  │
│  ║          │                         │                         │                ║  │
│  ║          ▼                         ▼                         ▼                ║  │
│  ║   ┌─────────────┐           ┌─────────────┐           ┌─────────────┐         ║  │
│  ║   │ Enterprise  │           │  System     │           │  External   │         ║  │
│  ║   │ MCP Servers │           │ MCP Servers │           │ MCP Servers │         ║  │
│  ║   │             │           │             │           │             │         ║  │
│  ║   │• ServiceNow │           │• File System│           │• Web Search │         ║  │
│  ║   │• D365       │           │• Database   │           │• Web Fetch  │         ║  │
│  ║   │• SharePoint │           │• Bash/Shell │           │• GitHub     │         ║  │
│  ║   │• Teams      │           │• Kubernetes │           │• StackOverflow│       ║  │
│  ║   │• Graph API  │           │• Azure CLI  │           │             │         ║  │
│  ║   │• SAP        │           │• SSH        │           │             │         ║  │
│  ║   └─────────────┘           └─────────────┘           └─────────────┘         ║  │
│  ║                                                                                ║  │
│  ╚════════════════════════════════════════════════════════════════════════════════╝  │
│                                                                                      │
│  ╔════════════════════════════════════════════════════════════════════════════════╗  │
│  ║                              可觀測性層                                        ║  │
│  ╠════════════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                                ║  │
│  ║   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          ║  │
│  ║   │ Azure       │  │ Application │  │ Log         │  │ Grafana     │          ║  │
│  ║   │ Monitor     │  │ Insights    │  │ Analytics   │  │ Dashboard   │          ║  │
│  ║   │ (Metrics)   │  │ (Traces)    │  │ (Logs)      │  │ (Viz)       │          ║  │
│  ║   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘          ║  │
│  ║                                                                                ║  │
│  ╚════════════════════════════════════════════════════════════════════════════════╝  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 組件詳細說明

#### 2.2.1 MAF Orchestrator Service

```python
# maf_orchestrator_service.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
from agent_framework import ChatAgent, WorkflowBuilder, MagenticBuilder
from agent_framework.anthropic import AnthropicClient
from agent_framework.checkpoint import CosmosDBCheckpointStorage
from agent_framework.ag_ui import AGUIServer

class EventPriority(Enum):
    CRITICAL = "critical"   # 生產系統故障
    HIGH = "high"           # 影響業務運營
    MEDIUM = "medium"       # 一般服務請求
    LOW = "low"             # 資訊查詢

class RiskLevel(Enum):
    LOW = "low"             # 自動執行
    MEDIUM = "medium"       # 記錄審計
    HIGH = "high"           # 需要審批
    CRITICAL = "critical"   # 多重審批

@dataclass
class ITEvent:
    """IT 事件結構"""
    event_id: str
    source: str                     # servicenow, teams, prometheus, defender
    type: str                       # incident, request, alert, security
    priority: EventPriority
    title: str
    description: str
    affected_systems: List[str]
    reporter: str
    metadata: Dict[str, Any]


class MAFOrchestratorService:
    """
    MAF 編排服務
    
    職責：
    1. 接收和分類 IT 事件
    2. 評估風險等級
    3. 選擇適當的工作流程
    4. 分派任務到 Worker
    5. 管理人機協作
    6. 記錄審計日誌
    """
    
    def __init__(self, config: "OrchestratorConfig"):
        self.config = config
        
        # 初始化 MAF Orchestrator Agent（使用 Claude Sonnet）
        self.orchestrator_agent = AnthropicClient(
            model_id="claude-sonnet-4-5-20250929"
        ).create_agent(
            name="ITOrchestratorAgent",
            instructions=self._get_orchestrator_instructions()
        )
        
        # 初始化組件
        self.intent_router = IntentRouter()
        self.risk_assessor = RiskAssessor()
        self.hitl_manager = HITLManager()
        self.task_dispatcher = TaskDispatcher()
        self.checkpoint_storage = CosmosDBCheckpointStorage(
            connection_string=config.cosmos_connection
        )
        self.audit_logger = AuditLogger()
        self.agui_server = AGUIServer()
    
    async def process_event(self, event: ITEvent) -> "ProcessingResult":
        """處理 IT 事件的主流程"""
        
        # 1. 記錄事件接收
        await self.audit_logger.log_event_received(event)
        
        # 2. 意圖識別和分類
        intent = await self.intent_router.classify(event)
        
        # 3. 風險評估
        risk = await self.risk_assessor.assess(event, intent)
        
        # 4. 選擇工作流程
        workflow = await self._select_workflow(event, intent, risk)
        
        # 5. 檢查是否需要人工審批
        if risk.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            approval = await self.hitl_manager.request_approval(
                event=event,
                risk=risk,
                workflow=workflow
            )
            if not approval.approved:
                return ProcessingResult(
                    status="rejected",
                    reason=approval.reason
                )
        
        # 6. 建立 Checkpoint
        checkpoint_id = await self.checkpoint_storage.create_checkpoint(
            event_id=event.event_id,
            workflow=workflow,
            state="initialized"
        )
        
        # 7. 執行工作流程
        try:
            result = await self._execute_workflow(
                workflow=workflow,
                event=event,
                checkpoint_id=checkpoint_id
            )
            
            # 8. 記錄完成
            await self.audit_logger.log_event_completed(event, result)
            
            return result
            
        except Exception as e:
            # 錯誤時恢復到最後檢查點
            await self._recover_from_checkpoint(checkpoint_id)
            raise
    
    async def _select_workflow(
        self, 
        event: ITEvent, 
        intent: "Intent",
        risk: "RiskAssessment"
    ) -> "Workflow":
        """根據事件類型選擇工作流程"""
        
        if intent.type == "etl_pipeline_failure":
            # 複雜故障排查 → Magentic 模式（動態規劃）
            return self._create_magentic_workflow(event)
        
        elif intent.type == "password_reset":
            # 簡單請求 → Sequential 模式
            return self._create_sequential_workflow(event)
        
        elif intent.type == "security_incident":
            # 安全事件 → Handoff 模式（專家路由）
            return self._create_handoff_workflow(event)
        
        else:
            # 一般事件 → GroupChat 模式（協作診斷）
            return self._create_groupchat_workflow(event)
    
    def _create_magentic_workflow(self, event: ITEvent) -> "Workflow":
        """創建 Magentic 工作流程（用於複雜問題）"""
        
        return (MagenticBuilder()
            .participants(
                diagnostician=self._create_worker_reference("diagnostic"),
                remediator=self._create_worker_reference("remediation"),
                verifier=self._create_worker_reference("verification")
            )
            .with_standard_manager(
                agent=self.orchestrator_agent,
                max_round_count=10,
                max_stall_count=3,
                max_reset_count=2
            )
            .with_plan_review()              # 人工審查計劃
            .with_human_input_on_stall()     # 卡住時請求人工介入
            .with_checkpointing(self.checkpoint_storage)
            .build())
    
    def _get_orchestrator_instructions(self) -> str:
        """Orchestrator Agent 的系統指令"""
        return """
        你是 APAC Glider IT 運維平台的編排協調者。
        
        你的職責是：
        1. 分析 IT 事件並制定處理計劃
        2. 協調多個專業 Worker 完成任務
        3. 在遇到困難時尋求人工協助
        4. 確保所有操作都有適當的審計記錄
        
        你可以使用的 Worker：
        - Diagnostic Worker：負責問題診斷和根因分析
        - Remediation Worker：負責問題修復和變更執行
        - Verification Worker：負責驗證修復結果
        
        重要原則：
        - 生產環境變更必須經過人工審批
        - 所有操作必須記錄到審計日誌
        - 遇到不確定情況時，請求人工介入
        """


class IntentRouter:
    """意圖識別和路由

    **實現說明 (2026-01-14 更新)**:
    實際實現使用規則驅動的 RuleBasedClassifier，而非 LLM 驅動分類。
    位置: backend/src/integrations/hybrid/intent/classifiers/rule_based.py

    原因:
    - 規則驅動提供更可預測、更快的響應時間 (<50ms)
    - 100+ 雙語關鍵字支援中英文意圖識別
    - LLMBasedClassifier 設計為可選 fallback，尚未實現
    """

    def __init__(self):
        # 實際實現使用 RuleBasedClassifier
        self._classifier = RuleBasedClassifier()

    async def classify(self, event: ITEvent) -> "Intent":
        """識別事件意圖 (規則驅動)"""

        # 使用規則分類器進行意圖識別
        classification = self._classifier.classify(
            text=f"{event.title} {event.description}",
            context={"source": event.source, "systems": event.affected_systems}
        )

        return Intent(
            type=classification.intent_type,
            confidence=classification.confidence,
            entities=classification.entities,
            suggested_workflow=classification.suggested_workflow
        )


class RuleBasedClassifier:
    """規則驅動分類器 (實際實現)

    特點:
    - 使用 100+ 雙語關鍵字 (WORKFLOW_KEYWORDS, CHAT_KEYWORDS)
    - 基於模式匹配和權重計算
    - 支援複雜度分析和多代理檢測
    - 響應時間 <50ms
    """

    WORKFLOW_KEYWORDS = [
        # 中文工作流程關鍵字
        "執行", "建立", "部署", "處理", "分析", "生成報告",
        # 英文工作流程關鍵字
        "execute", "create", "deploy", "process", "analyze", "generate"
    ]

    CHAT_KEYWORDS = [
        # 中文對話關鍵字
        "什麼是", "如何", "為什麼", "解釋", "說明",
        # 英文對話關鍵字
        "what is", "how to", "why", "explain", "describe"
    ]

    def classify(self, text: str, context: dict) -> "ClassificationResult":
        """使用規則進行分類"""

        # 關鍵字匹配和權重計算
        workflow_score = self._calculate_keyword_score(text, self.WORKFLOW_KEYWORDS)
        chat_score = self._calculate_keyword_score(text, self.CHAT_KEYWORDS)

        # 決定意圖類型
        if workflow_score > chat_score:
            intent_type = self._determine_workflow_type(text, context)
        else:
            intent_type = "conversational"

        return ClassificationResult(
            intent_type=intent_type,
            confidence=max(workflow_score, chat_score),
            entities=self._extract_entities(text),
            suggested_workflow=self._suggest_workflow(intent_type)
        )

    def _calculate_keyword_score(self, text: str, keywords: list) -> float:
        """計算關鍵字匹配分數"""
        # 實際實現詳見 rule_based.py
        pass


class RiskAssessor:
    """風險評估器"""
    
    async def assess(self, event: ITEvent, intent: "Intent") -> "RiskAssessment":
        """評估事件處理的風險等級"""
        
        risk_score = 0.0
        risk_factors = []
        
        # 評估因素 1：受影響系統的關鍵性
        critical_systems = ["production-db", "apac-glider", "sap-integration"]
        for system in event.affected_systems:
            if system in critical_systems:
                risk_score += 0.3
                risk_factors.append(f"關鍵系統受影響: {system}")
        
        # 評估因素 2：變更類型
        if intent.type in ["database_modification", "config_change"]:
            risk_score += 0.2
            risk_factors.append("涉及數據或配置變更")
        
        # 評估因素 3：影響範圍
        if len(event.affected_systems) > 3:
            risk_score += 0.2
            risk_factors.append(f"影響範圍廣: {len(event.affected_systems)} 個系統")
        
        # 評估因素 4：事件優先級
        if event.priority == EventPriority.CRITICAL:
            risk_score += 0.1
            risk_factors.append("關鍵優先級事件")
        
        # 確定風險等級
        if risk_score >= 0.8:
            level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            level = RiskLevel.HIGH
        elif risk_score >= 0.3:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        return RiskAssessment(
            level=level,
            score=risk_score,
            factors=risk_factors,
            requires_approval=level in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            approvers=self._get_required_approvers(level)
        )
    
    def _get_required_approvers(self, level: RiskLevel) -> List[str]:
        """獲取所需審批人"""
        
        if level == RiskLevel.CRITICAL:
            return ["IT Manager", "Change Advisory Board"]
        elif level == RiskLevel.HIGH:
            return ["IT Manager"]
        else:
            return []


class HITLManager:
    """人機協作管理器"""
    
    async def request_approval(
        self, 
        event: ITEvent, 
        risk: "RiskAssessment",
        workflow: "Workflow"
    ) -> "ApprovalResult":
        """請求人工審批"""
        
        # 1. 創建審批請求
        approval_request = ApprovalRequest(
            event_id=event.event_id,
            title=f"需要審批: {event.title}",
            description=self._build_approval_description(event, risk, workflow),
            risk_level=risk.level,
            required_approvers=risk.approvers,
            timeout_minutes=30,
            escalation_path=["IT Director"]
        )
        
        # 2. 發送到 Teams（通過 MCP）
        await self._send_approval_request_to_teams(approval_request)
        
        # 3. 等待審批結果
        result = await self._wait_for_approval(approval_request)
        
        return result
    
    def _build_approval_description(
        self, 
        event: ITEvent, 
        risk: "RiskAssessment",
        workflow: "Workflow"
    ) -> str:
        """構建審批請求描述"""
        
        return f"""
        ## 事件概要
        - **事件 ID**: {event.event_id}
        - **標題**: {event.title}
        - **來源**: {event.source}
        - **優先級**: {event.priority.value}
        
        ## 風險評估
        - **風險等級**: {risk.level.value}
        - **風險分數**: {risk.score:.2f}
        - **風險因素**:
          {chr(10).join(f"  - {f}" for f in risk.factors)}
        
        ## 計劃的工作流程
        {workflow.description}
        
        ## 可能的影響
        - 受影響系統: {', '.join(event.affected_systems)}
        
        請審批或拒絕此操作。
        """
```

#### 2.2.2 Claude Worker Service

```python
# claude_worker_service.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition
from mcp_gateway import MCPGatewayClient

@dataclass
class WorkerTask:
    """Worker 任務結構"""
    task_id: str
    event_id: str
    worker_type: str        # diagnostic, remediation, verification
    instructions: str
    context: Dict[str, Any]
    allowed_tools: List[str]
    timeout_seconds: int
    checkpoint_id: str


class ClaudeWorkerService:
    """
    Claude Worker 服務
    
    運行在容器中，使用 Claude Agent SDK 執行任務
    """
    
    def __init__(self, config: "WorkerConfig"):
        self.config = config
        self.mcp_gateway = MCPGatewayClient(config.mcp_gateway_url)
        
        # Worker 類型定義
        self.worker_definitions = {
            "diagnostic": self._create_diagnostic_worker(),
            "remediation": self._create_remediation_worker(),
            "verification": self._create_verification_worker()
        }
    
    def _create_diagnostic_worker(self) -> AgentDefinition:
        """創建診斷 Worker"""
        
        return AgentDefinition(
            description="IT 系統診斷專家，負責問題分析和根因識別",
            prompt="""
            你是 APAC Glider IT 運維平台的診斷專家。
            
            你的職責是：
            1. 分析系統日誌和錯誤訊息
            2. 識別問題的根本原因
            3. 收集相關診斷資訊
            4. 提供修復建議
            
            你可以使用的工具：
            - 檔案系統工具（Read, Grep, Glob）- 分析日誌
            - 資料庫查詢（MCP: database）- 查詢系統狀態
            - ServiceNow（MCP: servicenow）- 查詢歷史事件
            - Kubernetes（MCP: kubernetes）- 檢查容器狀態
            - Azure CLI（MCP: azure_cli）- 檢查雲端資源
            
            重要原則：
            - 使用延伸思考來分析複雜問題
            - 收集足夠的證據再下結論
            - 記錄所有診斷步驟
            - 如果需要更多資訊，可以委派子任務
            """,
            tools=["Read", "Grep", "Glob"],
            model="sonnet"
        )
    
    def _create_remediation_worker(self) -> AgentDefinition:
        """創建修復 Worker"""
        
        return AgentDefinition(
            description="IT 系統修復專家，負責執行修復操作",
            prompt="""
            你是 APAC Glider IT 運維平台的修復專家。
            
            你的職責是：
            1. 根據診斷結果執行修復操作
            2. 執行配置變更和腳本
            3. 協調跨系統的修復動作
            4. 記錄所有變更
            
            你可以使用的工具：
            - 檔案系統工具（Read, Write, Edit）- 修改配置
            - Bash 命令（Bash）- 執行腳本
            - Azure CLI（MCP: azure_cli）- 管理雲端資源
            - Kubernetes（MCP: kubernetes）- 管理容器
            - ServiceNow（MCP: servicenow）- 更新工單狀態
            
            重要原則：
            - 執行任何變更前先備份
            - 使用延伸思考來規劃修復步驟
            - 每個步驟都要驗證結果
            - 危險操作（如刪除、重啟）需要確認
            - 所有操作都要記錄到變更日誌
            """,
            tools=["Read", "Write", "Edit", "Bash"],
            model="sonnet"
        )
    
    def _create_verification_worker(self) -> AgentDefinition:
        """創建驗證 Worker"""
        
        return AgentDefinition(
            description="IT 系統驗證專家，負責驗證修復結果",
            prompt="""
            你是 APAC Glider IT 運維平台的驗證專家。
            
            你的職責是：
            1. 驗證修復操作是否成功
            2. 執行功能測試
            3. 檢查系統指標
            4. 確認業務流程恢復正常
            
            你可以使用的工具：
            - 檔案系統工具（Read, Grep）- 檢查日誌
            - 資料庫查詢（MCP: database）- 驗證數據
            - Prometheus（MCP: prometheus）- 檢查指標
            - Web Fetch（WebFetch）- 測試 API
            
            重要原則：
            - 快速但全面的驗證
            - 使用客觀指標判斷
            - 發現問題立即報告
            """,
            tools=["Read", "Grep", "WebFetch"],
            model="haiku"  # 使用更快的模型
        )
    
    async def execute_task(self, task: WorkerTask) -> "TaskResult":
        """執行 Worker 任務"""
        
        # 1. 獲取 Worker 定義
        worker_def = self.worker_definitions.get(task.worker_type)
        if not worker_def:
            raise ValueError(f"Unknown worker type: {task.worker_type}")
        
        # 2. 配置 MCP 工具（通過統一網關）
        mcp_servers = await self._configure_mcp_tools(task)
        
        # 3. 構建 Claude Agent SDK 選項
        options = ClaudeAgentOptions(
            model=worker_def.model,
            permission_mode="acceptEdits",
            
            # 延伸思考（用於複雜問題）
            max_thinking_tokens=10000 if task.worker_type != "verification" else 2000,
            
            # 工具配置
            allowed_tools=task.allowed_tools + worker_def.tools,
            mcp_servers=mcp_servers,
            
            # 子 Agent 定義（用於任務委派）
            agents=self._get_subagent_definitions(task.worker_type),
            
            # 串流配置
            include_partial_messages=True,
        )
        
        # 4. 構建完整提示
        prompt = self._build_task_prompt(task, worker_def)
        
        # 5. 執行 Claude Agent SDK
        result_content = []
        tool_calls = []
        thinking_content = []
        
        async for message in query(prompt=prompt, options=options):
            # 收集結果
            if self._is_text_message(message):
                result_content.append(message.text)
            elif self._is_tool_call(message):
                tool_calls.append(message.tool_call)
            elif self._is_thinking(message):
                thinking_content.append(message.thinking)
            
            # 發送進度到 Orchestrator
            await self._report_progress(task, message)
        
        # 6. 構建任務結果
        return TaskResult(
            task_id=task.task_id,
            status="completed",
            content="\n".join(result_content),
            tool_calls=tool_calls,
            thinking=thinking_content,
            metrics=self._collect_metrics()
        )
    
    async def _configure_mcp_tools(self, task: WorkerTask) -> Dict[str, Any]:
        """配置 MCP 工具（通過統一網關）"""
        
        # 所有 MCP 工具都通過統一網關存取
        # 網關負責：權限檢查、速率限制、審計日誌
        
        return {
            "gateway": {
                "type": "sse",
                "url": f"{self.mcp_gateway.base_url}/mcp/sse",
                "headers": {
                    "X-Task-ID": task.task_id,
                    "X-Event-ID": task.event_id,
                    "X-Worker-Type": task.worker_type,
                    "Authorization": f"Bearer {self.mcp_gateway.get_token()}"
                }
            }
        }
    
    def _get_subagent_definitions(self, worker_type: str) -> Dict[str, AgentDefinition]:
        """獲取子 Agent 定義"""
        
        if worker_type == "diagnostic":
            return {
                "log-analyzer": AgentDefinition(
                    description="專門分析日誌的子 Agent",
                    prompt="你專門分析系統日誌，找出錯誤模式和異常...",
                    tools=["Read", "Grep"],
                    model="haiku"
                ),
                "metrics-checker": AgentDefinition(
                    description="專門檢查系統指標的子 Agent",
                    prompt="你專門檢查 Prometheus 指標，識別異常趨勢...",
                    tools=["Read"],
                    model="haiku"
                )
            }
        
        elif worker_type == "remediation":
            return {
                "config-editor": AgentDefinition(
                    description="專門編輯配置文件的子 Agent",
                    prompt="你專門安全地編輯配置文件...",
                    tools=["Read", "Edit"],
                    model="haiku"
                ),
                "script-runner": AgentDefinition(
                    description="專門執行修復腳本的子 Agent",
                    prompt="你專門執行和驗證修復腳本...",
                    tools=["Bash", "Read"],
                    model="haiku"
                )
            }
        
        return {}
    
    def _build_task_prompt(self, task: WorkerTask, worker_def: AgentDefinition) -> str:
        """構建任務提示"""
        
        return f"""
        {worker_def.prompt}
        
        ## 當前任務
        
        **任務 ID**: {task.task_id}
        **事件 ID**: {task.event_id}
        
        **任務指令**:
        {task.instructions}
        
        **上下文資訊**:
        ```json
        {json.dumps(task.context, indent=2, ensure_ascii=False)}
        ```
        
        **可用工具**:
        - 內建工具: {', '.join(worker_def.tools)}
        - MCP 工具 (通過 gateway): {', '.join(task.allowed_tools)}
        
        請開始執行任務。使用延伸思考來分析問題，然後逐步執行。
        """
```

#### 2.2.3 統一 MCP 工具層

```python
# mcp_gateway_service.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
import asyncio

class ToolCategory(Enum):
    ENTERPRISE = "enterprise"   # ServiceNow, D365, SharePoint
    SYSTEM = "system"           # File, Database, Bash
    EXTERNAL = "external"       # Web, GitHub

@dataclass
class ToolPermission:
    """工具權限定義"""
    tool_name: str
    allowed_operations: List[str]
    allowed_targets: List[str]      # 允許的目標（路徑、系統等）
    denied_patterns: List[str]      # 禁止的模式
    requires_approval: bool
    rate_limit: int                 # 每分鐘調用次數
    audit_level: str                # minimal, standard, detailed


class MCPGatewayService:
    """
    統一 MCP 工具網關
    
    職責：
    1. 統一工具存取入口
    2. 權限控制和驗證
    3. 速率限制
    4. 審計日誌
    5. 熔斷保護
    """
    
    def __init__(self, config: "GatewayConfig"):
        self.config = config
        self.permission_manager = PermissionManager()
        self.rate_limiter = RateLimiter()
        self.audit_logger = AuditLogger()
        self.circuit_breaker = CircuitBreaker()
        
        # 初始化 MCP 伺服器連接
        self.mcp_servers = self._initialize_mcp_servers()
    
    def _initialize_mcp_servers(self) -> Dict[str, "MCPServer"]:
        """初始化所有 MCP 伺服器"""
        
        return {
            # 企業系統
            "servicenow": ServiceNowMCPServer(self.config.servicenow),
            "dynamics365": Dynamics365MCPServer(self.config.d365),
            "sharepoint": SharePointMCPServer(self.config.sharepoint),
            "teams": TeamsMCPServer(self.config.teams),
            "graph_api": GraphAPIMCPServer(self.config.graph),
            "sap": SAPMCPServer(self.config.sap),
            
            # 系統工具
            "database": DatabaseMCPServer(self.config.database),
            "kubernetes": KubernetesMCPServer(self.config.kubernetes),
            "azure_cli": AzureCLIMCPServer(self.config.azure),
            "ssh": SSHMCPServer(self.config.ssh),
            
            # 外部服務
            "web_search": WebSearchMCPServer(self.config.web_search),
            "github": GitHubMCPServer(self.config.github),
        }
    
    async def execute_tool(
        self,
        request: "ToolExecutionRequest",
        auth_context: "AuthContext"
    ) -> "ToolExecutionResult":
        """執行工具調用"""
        
        tool_name = request.tool_name
        operation = request.operation
        parameters = request.parameters
        
        # 1. 權限檢查
        permission = await self.permission_manager.check_permission(
            tool_name=tool_name,
            operation=operation,
            parameters=parameters,
            context=auth_context
        )
        
        if not permission.allowed:
            await self.audit_logger.log_denied(request, auth_context, permission.reason)
            raise PermissionDeniedError(permission.reason)
        
        # 2. 速率限制檢查
        if not await self.rate_limiter.check(tool_name, auth_context):
            await self.audit_logger.log_rate_limited(request, auth_context)
            raise RateLimitExceededError(f"Rate limit exceeded for {tool_name}")
        
        # 3. 熔斷檢查
        if self.circuit_breaker.is_open(tool_name):
            await self.audit_logger.log_circuit_open(request, auth_context)
            raise ServiceUnavailableError(f"Service {tool_name} is temporarily unavailable")
        
        # 4. 審計日誌（執行前）
        audit_id = await self.audit_logger.log_execution_start(request, auth_context)
        
        try:
            # 5. 執行工具
            server = self.mcp_servers.get(tool_name)
            if not server:
                raise ToolNotFoundError(f"Tool {tool_name} not found")
            
            result = await server.execute(operation, parameters)
            
            # 6. 審計日誌（執行後）
            await self.audit_logger.log_execution_success(audit_id, result)
            
            return result
            
        except Exception as e:
            # 7. 錯誤處理和熔斷更新
            self.circuit_breaker.record_failure(tool_name)
            await self.audit_logger.log_execution_failure(audit_id, e)
            raise


class PermissionManager:
    """權限管理器"""
    
    def __init__(self):
        # 載入權限配置
        self.permissions = self._load_permissions()
    
    def _load_permissions(self) -> Dict[str, ToolPermission]:
        """載入工具權限配置"""
        
        return {
            # ServiceNow 權限
            "servicenow": ToolPermission(
                tool_name="servicenow",
                allowed_operations=["query", "get", "create", "update"],
                allowed_targets=["incident", "request", "change"],
                denied_patterns=["delete_*", "admin_*"],
                requires_approval=False,
                rate_limit=100,
                audit_level="standard"
            ),
            
            # 資料庫權限
            "database": ToolPermission(
                tool_name="database",
                allowed_operations=["query", "select"],
                allowed_targets=["apac_glider_*", "reporting_*"],
                denied_patterns=["drop_*", "delete_*", "truncate_*", "alter_*"],
                requires_approval=False,
                rate_limit=50,
                audit_level="detailed"
            ),
            
            # Kubernetes 權限
            "kubernetes": ToolPermission(
                tool_name="kubernetes",
                allowed_operations=["get", "describe", "logs", "scale", "rollout"],
                allowed_targets=["deployment/*", "pod/*", "service/*"],
                denied_patterns=["delete_*", "exec_*"],
                requires_approval=True,  # 需要審批
                rate_limit=30,
                audit_level="detailed"
            ),
            
            # SSH 權限（高風險）
            "ssh": ToolPermission(
                tool_name="ssh",
                allowed_operations=["execute"],
                allowed_targets=["app-server-*", "etl-server-*"],
                denied_patterns=["rm -rf *", "shutdown", "reboot", "passwd"],
                requires_approval=True,  # 需要審批
                rate_limit=10,
                audit_level="detailed"
            ),
            
            # Azure CLI 權限
            "azure_cli": ToolPermission(
                tool_name="azure_cli",
                allowed_operations=["az storage", "az datafactory", "az monitor"],
                allowed_targets=["rg-apac-*", "adf-apac-*"],
                denied_patterns=["az ad *", "az role *", "az keyvault *"],
                requires_approval=False,
                rate_limit=50,
                audit_level="standard"
            ),
        }
    
    async def check_permission(
        self,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        context: "AuthContext"
    ) -> "PermissionCheckResult":
        """檢查權限"""
        
        permission = self.permissions.get(tool_name)
        if not permission:
            return PermissionCheckResult(allowed=False, reason="Tool not configured")
        
        # 檢查操作是否允許
        if operation not in permission.allowed_operations:
            return PermissionCheckResult(
                allowed=False, 
                reason=f"Operation {operation} not allowed for {tool_name}"
            )
        
        # 檢查目標是否允許
        target = parameters.get("target", "")
        if not self._match_patterns(target, permission.allowed_targets):
            return PermissionCheckResult(
                allowed=False,
                reason=f"Target {target} not in allowed list"
            )
        
        # 檢查是否匹配禁止模式
        command = parameters.get("command", "")
        if self._match_patterns(command, permission.denied_patterns):
            return PermissionCheckResult(
                allowed=False,
                reason=f"Command matches denied pattern"
            )
        
        # 檢查是否需要審批
        if permission.requires_approval:
            # 檢查是否已有審批
            if not context.has_approval(tool_name, operation):
                return PermissionCheckResult(
                    allowed=False,
                    reason="Requires approval",
                    requires_approval=True
                )
        
        return PermissionCheckResult(allowed=True)


class AuditLogger:
    """審計日誌器"""
    
    def __init__(self, log_analytics_client: "LogAnalyticsClient"):
        self.client = log_analytics_client
    
    async def log_execution_start(
        self, 
        request: "ToolExecutionRequest",
        context: "AuthContext"
    ) -> str:
        """記錄執行開始"""
        
        audit_id = str(uuid.uuid4())
        
        await self.client.send_log({
            "audit_id": audit_id,
            "event_type": "tool_execution_start",
            "timestamp": datetime.utcnow().isoformat(),
            
            # 請求資訊
            "tool_name": request.tool_name,
            "operation": request.operation,
            "parameters_hash": self._hash_parameters(request.parameters),
            
            # 上下文資訊
            "task_id": context.task_id,
            "event_id": context.event_id,
            "worker_type": context.worker_type,
            
            # 來源資訊
            "source_ip": context.source_ip,
            "user_agent": context.user_agent,
        })
        
        return audit_id
    
    async def log_execution_success(self, audit_id: str, result: Any):
        """記錄執行成功"""
        
        await self.client.send_log({
            "audit_id": audit_id,
            "event_type": "tool_execution_success",
            "timestamp": datetime.utcnow().isoformat(),
            "result_summary": self._summarize_result(result),
        })
    
    async def log_execution_failure(self, audit_id: str, error: Exception):
        """記錄執行失敗"""
        
        await self.client.send_log({
            "audit_id": audit_id,
            "event_type": "tool_execution_failure",
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
        })
    
    async def log_denied(
        self, 
        request: "ToolExecutionRequest",
        context: "AuthContext",
        reason: str
    ):
        """記錄權限拒絕"""
        
        await self.client.send_log({
            "event_type": "permission_denied",
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": request.tool_name,
            "operation": request.operation,
            "reason": reason,
            "task_id": context.task_id,
        })
```

---

## 3. 完整場景執行流程

### 3.1 場景：ETL Pipeline 失敗

```
事件：用戶報告「APAC Glider ETL Pipeline 失敗，導致日報表無法生成」
```

### 3.2 執行時序圖

```
┌─────────┐ ┌─────────────┐ ┌───────────────┐ ┌─────────────┐ ┌───────────────┐ ┌─────────────┐
│  User   │ │Event Ingest │ │MAF Orchestrator│ │Claude Worker│ │  MCP Gateway  │ │  外部系統   │
└────┬────┘ └──────┬──────┘ └───────┬───────┘ └──────┬──────┘ └───────┬───────┘ └──────┬──────┘
     │             │                │                │                │                │
     │ 1. 報告問題 │                │                │                │                │
     │────────────▶│                │                │                │                │
     │             │                │                │                │                │
     │             │ 2. 創建事件   │                │                │                │
     │             │───────────────▶│                │                │                │
     │             │                │                │                │                │
     │             │                │ 3. 意圖識別    │                │                │
     │             │                │ (Claude Sonnet)│                │                │
     │             │                │────────────────│                │                │
     │             │                │                │                │                │
     │             │                │ 4. 風險評估    │                │                │
     │             │                │ → HIGH (生產系統)                │                │
     │             │                │────────────────│                │                │
     │             │                │                │                │                │
     │             │                │ 5. 請求人工審批│                │                │
     │             │                │════════════════│═══════════════▶│ Teams 通知    │
     │             │                │                │                │───────────────▶│
     │             │                │                │                │                │
     │ 6. IT Manager 審批         │                │                │                │
     │◀════════════════════════════│════════════════│═══════════════▶│◀───────────────│
     │             │                │                │                │                │
     │             │                │ 7. 創建 Checkpoint               │                │
     │             │                │────────────────│                │                │
     │             │                │                │                │                │
     │             │                │ 8. 分派診斷任務│                │                │
     │             │                │───────────────▶│                │                │
     │             │                │                │                │                │
     │             │                │                │ 9a. 查詢 ServiceNow            │
     │             │                │                │───────────────▶│───────────────▶│
     │             │                │                │◀───────────────│◀───────────────│
     │             │                │                │                │                │
     │             │                │                │ 9b. 查詢 ADF 狀態              │
     │             │                │                │───────────────▶│───────────────▶│
     │             │                │                │◀───────────────│◀───────────────│
     │             │                │                │                │                │
     │             │                │                │ 9c. 分析日誌   │                │
     │             │                │                │ (延伸思考)     │                │
     │             │                │                │────────────────│                │
     │             │                │                │                │                │
     │             │                │                │ 9d. 委派子Agent│                │
     │             │                │                │ (log-analyzer) │                │
     │             │                │                │────────────────│                │
     │             │                │                │                │                │
     │             │                │ 10. 診斷完成   │                │                │
     │             │                │◀───────────────│                │                │
     │             │                │ 根因：配置錯誤 │                │                │
     │             │                │                │                │                │
     │             │                │ 11. 更新 Checkpoint              │                │
     │             │                │────────────────│                │                │
     │             │                │                │                │                │
     │             │                │ 12. 分派修復任務                 │                │
     │             │                │───────────────▶│                │                │
     │             │                │                │                │                │
     │             │                │                │ 13a. 備份配置  │                │
     │             │                │                │───────────────▶│───────────────▶│
     │             │                │                │◀───────────────│◀───────────────│
     │             │                │                │                │                │
     │             │                │                │ 13b. 修改配置  │                │
     │             │                │                │ (延伸思考規劃) │                │
     │             │                │                │───────────────▶│───────────────▶│
     │             │                │                │◀───────────────│◀───────────────│
     │             │                │                │                │                │
     │             │                │                │ 13c. 觸發重新運行               │
     │             │                │                │───────────────▶│───────────────▶│
     │             │                │                │◀───────────────│◀───────────────│
     │             │                │                │                │                │
     │             │                │ 14. 修復完成   │                │                │
     │             │                │◀───────────────│                │                │
     │             │                │                │                │                │
     │             │                │ 15. 更新 Checkpoint              │                │
     │             │                │────────────────│                │                │
     │             │                │                │                │                │
     │             │                │ 16. 分派驗證任務                 │                │
     │             │                │───────────────▶│ (Haiku 快速)   │                │
     │             │                │                │                │                │
     │             │                │                │ 17a. 檢查 Pipeline 狀態         │
     │             │                │                │───────────────▶│───────────────▶│
     │             │                │                │◀───────────────│◀───────────────│
     │             │                │                │                │                │
     │             │                │                │ 17b. 驗證報表生成               │
     │             │                │                │───────────────▶│───────────────▶│
     │             │                │                │◀───────────────│◀───────────────│
     │             │                │                │                │                │
     │             │                │ 18. 驗證通過   │                │                │
     │             │                │◀───────────────│                │                │
     │             │                │                │                │                │
     │             │                │ 19. 關閉 ServiceNow 工單         │                │
     │             │                │═══════════════▶│═══════════════▶│───────────────▶│
     │             │                │                │                │                │
     │             │                │ 20. 發送完成通知                 │                │
     │             │                │═══════════════▶│═══════════════▶│ Teams 通知    │
     │             │                │                │                │───────────────▶│
     │             │                │                │                │                │
     │ 21. 收到通知│                │                │                │                │
     │◀════════════════════════════│════════════════│════════════════│◀───────────────│
     │             │                │                │                │                │
```

### 3.3 各階段詳細說明

#### 階段 1-2：事件接收

```python
# 用戶通過 Teams 報告問題
user_message = """
ETL Pipeline 今天早上失敗了，日報表沒有生成。
錯誤訊息：ADF Pipeline 'DailyReportPipeline' failed at activity 'CopyToDataWarehouse'
需要盡快修復，影響業務報告。
"""

# Event Ingestion API 創建事件
event = ITEvent(
    event_id="EVT-2026-01-10-001",
    source="teams",
    type="incident",
    priority=EventPriority.HIGH,
    title="ETL Pipeline 失敗 - 日報表無法生成",
    description=user_message,
    affected_systems=["apac-glider", "azure-data-factory", "sql-datawarehouse"],
    reporter="user@ricoh.com",
    metadata={
        "error_code": "ADF_ACTIVITY_FAILED",
        "pipeline_name": "DailyReportPipeline",
        "activity_name": "CopyToDataWarehouse"
    }
)
```

#### 階段 3-4：意圖識別和風險評估

```python
# MAF Orchestrator 使用 Claude Sonnet 進行意圖識別
intent = Intent(
    type="etl_pipeline_failure",
    confidence=0.95,
    entities={
        "pipeline": "DailyReportPipeline",
        "activity": "CopyToDataWarehouse",
        "service": "Azure Data Factory"
    },
    suggested_workflow="magentic"  # 複雜問題需要動態規劃
)

# 風險評估結果
risk = RiskAssessment(
    level=RiskLevel.HIGH,
    score=0.72,
    factors=[
        "關鍵系統受影響: apac-glider",
        "涉及數據或配置變更",
        "影響範圍廣: 3 個系統"
    ],
    requires_approval=True,
    approvers=["IT Manager"]
)
```

#### 階段 5-6：人工審批（HITL）

```python
# MAF 發送 Teams 審批請求
approval_request = ApprovalRequest(
    event_id="EVT-2026-01-10-001",
    title="需要審批: ETL Pipeline 修復",
    description="""
    ## 事件概要
    - **事件 ID**: EVT-2026-01-10-001
    - **標題**: ETL Pipeline 失敗 - 日報表無法生成
    - **優先級**: HIGH
    
    ## 風險評估
    - **風險等級**: HIGH (0.72)
    - **風險因素**:
      - 關鍵系統受影響: apac-glider
      - 涉及數據或配置變更
      - 影響範圍廣: 3 個系統
    
    ## 計劃的處理流程
    1. 診斷 Pipeline 失敗原因
    2. 修復配置或重新執行
    3. 驗證報表生成正常
    
    請審批或拒絕此操作。
    """,
    required_approvers=["IT Manager"],
    timeout_minutes=30
)

# IT Manager 審批通過
approval_result = ApprovalResult(
    approved=True,
    approver="it.manager@ricoh.com",
    timestamp="2026-01-10T09:15:00Z",
    comments="同意修復，請注意備份配置"
)
```

#### 階段 8-10：診斷階段（Claude Worker）

```python
# Diagnostic Worker 收到任務
diagnostic_task = WorkerTask(
    task_id="TASK-001-DIAG",
    event_id="EVT-2026-01-10-001",
    worker_type="diagnostic",
    instructions="""
    診斷 Azure Data Factory Pipeline 'DailyReportPipeline' 失敗的原因。
    
    已知資訊：
    - 失敗活動: CopyToDataWarehouse
    - 錯誤代碼: ADF_ACTIVITY_FAILED
    
    請執行以下步驟：
    1. 查詢 ServiceNow 歷史事件，看是否有類似問題
    2. 檢查 ADF Pipeline 運行狀態和錯誤詳情
    3. 分析相關日誌
    4. 識別根本原因
    """,
    context={
        "pipeline_name": "DailyReportPipeline",
        "activity_name": "CopyToDataWarehouse",
        "error_code": "ADF_ACTIVITY_FAILED"
    },
    allowed_tools=[
        "mcp__gateway__servicenow",
        "mcp__gateway__azure_cli",
        "mcp__gateway__database"
    ],
    timeout_seconds=600
)

# Claude Agent SDK 執行（帶延伸思考）
"""
<thinking>
讓我分析這個 ETL Pipeline 失敗問題...

首先，我需要了解：
1. Pipeline 的整體結構和依賴關係
2. CopyToDataWarehouse 活動的具體配置
3. 最近是否有任何變更

診斷策略：
1. 先查詢 ServiceNow 看歷史是否有類似問題
2. 使用 Azure CLI 獲取 Pipeline 運行詳情
3. 檢查源資料庫和目標資料庫的連接狀態
4. 分析錯誤日誌找出具體原因

讓我開始執行...
</thinking>
"""

# 工具調用 1: 查詢 ServiceNow
servicenow_query = {
    "operation": "query",
    "parameters": {
        "table": "incident",
        "query": "short_description LIKE '%DailyReportPipeline%'",
        "limit": 5
    }
}

# 工具調用 2: 檢查 ADF Pipeline 狀態
azure_cli_command = {
    "operation": "execute",
    "parameters": {
        "command": "az datafactory pipeline-run show --factory-name adf-apac-glider --resource-group rg-apac-data --run-id <latest_run_id>"
    }
}

# 工具調用 3: 委派子 Agent 分析日誌
subagent_task = {
    "tool": "Task",
    "parameters": {
        "agent": "log-analyzer",
        "prompt": "分析 /var/log/adf/pipeline_*.log 中最近的錯誤，特別關注連接超時和認證錯誤"
    }
}

# 診斷結果
diagnostic_result = {
    "root_cause": "SQL Server 連接字串配置錯誤",
    "details": """
    根據分析，Pipeline 失敗的根本原因是：
    
    1. 在 2026-01-09 的維護窗口中，SQL Server 連接端點發生了變更
    2. ADF 的連接字串配置未同步更新
    3. 導致 CopyToDataWarehouse 活動無法連接到目標資料庫
    
    相關證據：
    - ADF 錯誤日誌顯示 "Login timeout expired"
    - SQL Server 審計日誌顯示連接被拒絕
    - 上次成功運行是 2026-01-08
    """,
    "recommendation": "更新 ADF Linked Service 中的 SQL Server 連接字串"
}
```

#### 階段 12-14：修復階段（Claude Worker）

```python
# Remediation Worker 收到任務
remediation_task = WorkerTask(
    task_id="TASK-001-REMED",
    event_id="EVT-2026-01-10-001",
    worker_type="remediation",
    instructions="""
    根據診斷結果，修復 ADF Pipeline 連接配置問題。
    
    根因：SQL Server 連接字串配置錯誤
    
    請執行以下步驟：
    1. 備份當前 Linked Service 配置
    2. 更新 SQL Server 連接字串
    3. 測試連接
    4. 觸發 Pipeline 重新運行
    """,
    context={
        "pipeline_name": "DailyReportPipeline",
        "linked_service": "AzureSqlDW_LinkedService",
        "new_connection_endpoint": "sql-apac-glider-v2.database.windows.net"
    },
    allowed_tools=[
        "mcp__gateway__azure_cli",
        "mcp__gateway__database"
    ],
    timeout_seconds=900
)

# Claude Agent SDK 執行（帶延伸思考）
"""
<thinking>
這是一個生產環境變更，我需要非常謹慎。

修復計劃：
1. 首先備份當前配置 - 這是最重要的步驟
2. 驗證新的連接端點是否可達
3. 更新 Linked Service 配置
4. 測試連接
5. 觸發 Pipeline 運行
6. 監控運行狀態

每一步都需要驗證結果後再繼續...
</thinking>
"""

# 工具調用序列
tool_calls = [
    # 1. 備份配置
    {
        "tool": "mcp__gateway__azure_cli",
        "operation": "execute",
        "parameters": {
            "command": "az datafactory linked-service show --factory-name adf-apac-glider --name AzureSqlDW_LinkedService > /backup/linked_service_backup_20260110.json"
        }
    },
    
    # 2. 測試新端點連接
    {
        "tool": "mcp__gateway__database",
        "operation": "test_connection",
        "parameters": {
            "server": "sql-apac-glider-v2.database.windows.net",
            "database": "APACGliderDW"
        }
    },
    
    # 3. 更新配置
    {
        "tool": "mcp__gateway__azure_cli",
        "operation": "execute",
        "parameters": {
            "command": "az datafactory linked-service update --factory-name adf-apac-glider --name AzureSqlDW_LinkedService --properties @/config/updated_linked_service.json"
        }
    },
    
    # 4. 觸發 Pipeline
    {
        "tool": "mcp__gateway__azure_cli",
        "operation": "execute",
        "parameters": {
            "command": "az datafactory pipeline create-run --factory-name adf-apac-glider --name DailyReportPipeline"
        }
    }
]

# 修復結果
remediation_result = {
    "status": "completed",
    "changes": [
        "備份了原始 Linked Service 配置",
        "更新了 SQL Server 連接端點",
        "觸發了 Pipeline 重新運行 (run_id: xxx-xxx)"
    ],
    "rollback_info": {
        "backup_location": "/backup/linked_service_backup_20260110.json",
        "rollback_command": "az datafactory linked-service update ... --properties @/backup/linked_service_backup_20260110.json"
    }
}
```

#### 階段 16-18：驗證階段（Claude Worker）

```python
# Verification Worker 收到任務
verification_task = WorkerTask(
    task_id="TASK-001-VERIFY",
    event_id="EVT-2026-01-10-001",
    worker_type="verification",
    instructions="""
    驗證 ETL Pipeline 修復結果。
    
    請確認：
    1. Pipeline 運行成功完成
    2. 數據已正確寫入目標資料庫
    3. 日報表可以正常生成
    """,
    context={
        "pipeline_run_id": "xxx-xxx",
        "expected_table": "dbo.DailyReport"
    },
    allowed_tools=[
        "mcp__gateway__azure_cli",
        "mcp__gateway__database"
    ],
    timeout_seconds=300
)

# Claude Agent SDK 執行（使用 Haiku 快速驗證）
verification_result = {
    "status": "verified",
    "checks": [
        {
            "check": "Pipeline 運行狀態",
            "result": "Succeeded",
            "details": "Pipeline 在 5 分鐘內完成"
        },
        {
            "check": "數據寫入驗證",
            "result": "Passed",
            "details": "DailyReport 表有 2026-01-10 的數據，共 15,234 行"
        },
        {
            "check": "報表生成測試",
            "result": "Passed",
            "details": "可以成功查詢今日報表數據"
        }
    ],
    "conclusion": "修復成功，系統恢復正常運作"
}
```

#### 階段 19-21：完成和通知

```python
# 關閉 ServiceNow 工單
servicenow_update = {
    "operation": "update",
    "parameters": {
        "table": "incident",
        "sys_id": "INC0012345",
        "data": {
            "state": "Resolved",
            "resolution_code": "Fixed",
            "resolution_notes": """
            問題已解決。
            
            根因：SQL Server 連接端點變更後，ADF 配置未同步更新
            
            修復動作：
            1. 更新了 ADF Linked Service 的 SQL Server 連接字串
            2. 重新運行了 DailyReportPipeline
            3. 驗證了數據正確寫入和報表生成
            
            預防措施：
            - 建議在維護窗口後增加配置驗證步驟
            - 已添加連接監控告警
            """
        }
    }
}

# 發送 Teams 通知
teams_notification = {
    "to": ["user@ricoh.com", "it.manager@ricoh.com"],
    "subject": "✅ ETL Pipeline 問題已解決",
    "body": """
    您報告的 ETL Pipeline 問題已解決。
    
    **事件 ID**: EVT-2026-01-10-001
    **處理時間**: 45 分鐘
    
    **問題原因**: SQL Server 連接端點變更後配置未同步
    **解決方案**: 更新了 ADF 連接配置並重新運行 Pipeline
    **驗證結果**: 日報表已成功生成
    
    如有任何問題，請回覆此訊息。
    """
}
```

---

## 4. 關鍵設計決策說明

### 4.1 為什麼 MAF Orchestrator 使用 Claude 作為 LLM？

| 考量 | 說明 |
|------|------|
| **統一體驗** | 所有 Agent 都使用 Claude，行為一致 |
| **意圖識別** | Claude 在複雜意圖識別方面表現優秀 |
| **中文支援** | Claude 對中文的理解和生成更自然 |
| **成本效益** | Orchestrator 主要是決策，不需要延伸思考，可用 Sonnet |

### 4.2 為什麼 Worker 需要容器隔離？

| 原因 | 說明 |
|------|------|
| **安全隔離** | 每個 Worker 只能存取授權的資源 |
| **資源控制** | 可以限制 CPU、記憶體、網路 |
| **故障隔離** | 一個 Worker 失敗不影響其他 |
| **可擴展** | 可以根據負載動態擴展 Worker 數量 |

### 4.3 為什麼需要統一 MCP 工具層？

| 原因 | 說明 |
|------|------|
| **單一權限策略** | 所有工具存取都經過同一套權限檢查 |
| **集中審計** | 所有操作都有統一的審計日誌 |
| **速率控制** | 防止過度調用外部系統 |
| **熔斷保護** | 外部系統故障時自動降級 |

### 4.4 Checkpoint 策略

| 檢查點位置 | 目的 |
|------------|------|
| 審批後 | 確保已審批狀態不會丟失 |
| 每個 Worker 任務完成後 | 可以從失敗點恢復 |
| 關鍵變更前後 | 支援回滾 |

---

## 5. 可觀測性設計

### 5.1 指標 (Metrics)

```python
# 關鍵業務指標
metrics = {
    # 處理效率
    "event_processing_time": Histogram("處理時間分布"),
    "automation_rate": Gauge("自動化率"),
    "approval_wait_time": Histogram("審批等待時間"),
    
    # 系統健康
    "worker_pool_utilization": Gauge("Worker 利用率"),
    "mcp_gateway_latency": Histogram("MCP 網關延遲"),
    "checkpoint_count": Counter("Checkpoint 數量"),
    
    # 錯誤追蹤
    "event_failure_rate": Gauge("事件失敗率"),
    "tool_error_rate": Gauge("工具錯誤率"),
}
```

### 5.2 追蹤 (Tracing)

```python
# OpenTelemetry 追蹤
trace_attributes = {
    "event_id": "EVT-2026-01-10-001",
    "workflow_type": "magentic",
    "risk_level": "high",
    
    # Span 層級
    "spans": [
        "event_ingestion",
        "intent_classification",
        "risk_assessment",
        "approval_request",
        "diagnostic_worker",
        "remediation_worker",
        "verification_worker",
        "completion"
    ]
}
```

### 5.3 日誌 (Logging)

```python
# 結構化日誌
log_schema = {
    "timestamp": "ISO 8601",
    "level": "INFO/WARN/ERROR",
    "event_id": "關聯 ID",
    "component": "組件名稱",
    "action": "動作描述",
    "details": "詳細資訊",
    "duration_ms": "執行時間"
}
```

---

## 6. 總結

### 6.1 架構優勢

| 優勢 | 說明 |
|------|------|
| **可控** | MAF 編排層提供完整的流程控制 |
| **可觀測** | 統一的指標、追蹤、日誌 |
| **可治理** | 統一 MCP 層的權限和審計 |
| **智能** | Claude 的延伸思考和自主規劃 |
| **彈性** | Worker 容器化，可動態擴展 |
| **可恢復** | Checkpoint 支援故障恢復 |

### 6.2 關鍵設計原則

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   1. 分離關注點                                                          │
│      ─────────────                                                       │
│      MAF 負責「什麼」和「誰」，Claude 負責「怎麼做」                      │
│                                                                          │
│   2. 統一工具存取                                                        │
│      ─────────────                                                       │
│      所有工具通過 MCP Gateway，統一權限和審計                            │
│                                                                          │
│   3. 人機協作優先                                                        │
│      ─────────────                                                       │
│      高風險操作必須人工審批                                              │
│                                                                          │
│   4. 容錯設計                                                            │
│      ─────────────                                                       │
│      Checkpoint + 熔斷 + 回滾支援                                        │
│                                                                          │
│   5. 深度可觀測                                                          │
│      ─────────────                                                       │
│      每個步驟都有追蹤、指標、日誌                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.3 實施狀態 (2026-01-13 更新)

| 原計劃 | 實際實現 | 狀態 |
|-------|---------|------|
| Phase 17A: MAF Orchestrator + Claude LLM | Phase 12-13: Claude SDK Core + Hybrid Core | ✅ 已完成 |
| Phase 17B: Claude Worker 容器化 | Phase 21: Sandbox Security Architecture | 📋 計劃中 |
| Phase 17C: 統一 MCP Gateway | Phase 12: Claude MCP Integration | ✅ 已完成 |
| Phase 17D: 整合測試和可觀測性 | Phase 15-16: AG-UI + Unified Chat | ✅ 已完成 |

### 6.4 下一步計劃

1. **Phase 21**: 實現沙箱安全架構（進程隔離、IPC 通信）
2. **Phase 22**: Claude 自主能力與學習系統（mem0 整合）
3. **Phase 23**: 多 Agent 協調與主動巡檢（A2A 協議）

---

**文件結束**

---

## 更新歷史

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0 | 2026-01-10 | 初始版本，架構設計文檔 |
| 1.1 | 2026-01-13 | 添加實現狀態章節，Phase 7-11 替代說明，更新實施狀態 |
