"""Agent Skills — ITIL SOP knowledge packs for MAF Agents.

Provides structured enterprise knowledge as agent skills that can be
injected into the Orchestrator's context via FileAgentSkillsProvider
or directly as prompt context.

Sprint 119 — Phase 38 E2E Assembly C.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    """Categories of agent skills."""

    INCIDENT_MANAGEMENT = "incident_management"
    CHANGE_MANAGEMENT = "change_management"
    ENTERPRISE_ARCHITECTURE = "enterprise_architecture"
    GENERAL_IT = "general_it"


@dataclass
class AgentSkill:
    """A single structured knowledge skill."""

    skill_id: str
    name: str
    category: SkillCategory
    description: str
    content: str
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Built-in ITIL SOP Skills
# =============================================================================

INCIDENT_MANAGEMENT_SOP = AgentSkill(
    skill_id="itil-incident-mgmt-v1",
    name="ITIL Incident Management SOP",
    category=SkillCategory.INCIDENT_MANAGEMENT,
    description="標準 ITIL 事件管理流程，涵蓋事件識別到關閉的完整生命週期",
    tags=["itil", "incident", "sop", "it-ops"],
    content="""# ITIL Incident Management SOP

## 1. 事件識別與記錄
- 接收來源：用戶報告、監控告警、自動偵測
- 必填欄位：標題、描述、影響範圍、嚴重程度
- 自動分類：基於關鍵字和歷史模式

## 2. 事件分類與優先級
| 嚴重程度 | 影響 | 回應時間 | 解決時間 |
|---------|------|---------|---------|
| P1 Critical | 全公司服務中斷 | 15 分鐘 | 4 小時 |
| P2 High | 部門級服務受損 | 30 分鐘 | 8 小時 |
| P3 Medium | 個別用戶受影響 | 2 小時 | 24 小時 |
| P4 Low | 輕微不便 | 8 小時 | 72 小時 |

## 3. 初始診斷
- 檢查已知錯誤資料庫 (KEDB)
- 查詢相似事件歷史記錄
- 執行基本故障排除步驟
- 判斷是否需要升級

## 4. 升級路徑
- 功能升級：L1 → L2 → L3 技術支援
- 管理升級：超過 SLA 時間 → 通知主管
- 供應商升級：第三方系統問題 → 聯繫供應商

## 5. 解決與恢復
- 實施解決方案或臨時解決方法
- 驗證服務恢復正常
- 記錄解決步驟和根因

## 6. 事件關閉
- 確認用戶滿意
- 更新知識庫
- 記錄經驗教訓
- 觸發問題管理流程（如需要）
""",
)

CHANGE_MANAGEMENT_SOP = AgentSkill(
    skill_id="itil-change-mgmt-v1",
    name="ITIL Change Management SOP",
    category=SkillCategory.CHANGE_MANAGEMENT,
    description="標準 ITIL 變更管理流程，涵蓋變更請求到實施的完整生命週期",
    tags=["itil", "change", "sop", "cab"],
    content="""# ITIL Change Management SOP

## 1. 變更分類
| 類型 | 審批流程 | 風險等級 |
|------|---------|---------|
| 標準變更 | 預先審批，可自動執行 | 低 |
| 一般變更 | CAB 審批 | 中 |
| 緊急變更 | ECAB 快速審批 | 高 |

## 2. 變更請求 (RFC)
- 變更描述和理由
- 影響範圍評估
- 回退計劃
- 測試計劃
- 排程建議

## 3. 影響評估
- 服務影響分析
- 風險評估（7 維度）
- 資源需求
- 依賴關係確認

## 4. CAB 審批
- 每週 CAB 會議審查一般變更
- ECAB 可在 2 小時內召開
- 審批標準：風險可接受、回退計劃完整、測試通過

## 5. 實施
- 在維護窗口執行
- 按步驟文件操作
- 即時監控影響
- 準備回退方案

## 6. 驗證與關閉
- 確認變更成功
- 更新 CMDB
- 記錄實施結果
- 觸發事後審查（PIR）
""",
)

ENTERPRISE_ARCHITECTURE_REF = AgentSkill(
    skill_id="ea-reference-v1",
    name="Enterprise Architecture Reference",
    category=SkillCategory.ENTERPRISE_ARCHITECTURE,
    description="企業架構參考指南，包含系統拓撲、服務依賴、技術標準",
    tags=["architecture", "reference", "systems", "standards"],
    content="""# Enterprise Architecture Reference

## 核心系統架構
- **ERP**: SAP S/4HANA — 財務、採購、庫存
- **CRM**: Salesforce — 客戶管理、銷售流程
- **ITSM**: ServiceNow — IT 服務管理、事件追蹤
- **CI/CD**: Azure DevOps — 部署流水線
- **監控**: Grafana + Prometheus — 基礎設施監控

## 技術標準
- **程式語言**: Python 3.11+, TypeScript 5.0+, Java 17+
- **雲平台**: Azure (主要), AWS (備援)
- **容器化**: Docker + Kubernetes (AKS)
- **資料庫**: PostgreSQL 16 (OLTP), Cosmos DB (NoSQL)
- **快取**: Redis 7.0+
- **消息佇列**: RabbitMQ / Azure Service Bus

## 安全標準
- 所有 API 必須 HTTPS + JWT 認證
- 機敏資料加密 (AES-256)
- 定期安全掃描和滲透測試
- 符合 ISO 27001 標準
""",
)


class AgentSkillsProvider:
    """Provides agent skills to the Orchestrator.

    Manages built-in ITIL SOPs and custom skills, making them available
    as context for the Orchestrator Agent.
    """

    def __init__(self) -> None:
        self._skills: Dict[str, AgentSkill] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in ITIL SOP skills."""
        for skill in [
            INCIDENT_MANAGEMENT_SOP,
            CHANGE_MANAGEMENT_SOP,
            ENTERPRISE_ARCHITECTURE_REF,
        ]:
            self._skills[skill.skill_id] = skill
        logger.info("AgentSkillsProvider: %d built-in skills registered", len(self._skills))

    def register_skill(self, skill: AgentSkill) -> None:
        """Register a custom skill."""
        self._skills[skill.skill_id] = skill

    def get_skill(self, skill_id: str) -> Optional[AgentSkill]:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills(self, category: Optional[SkillCategory] = None) -> List[AgentSkill]:
        """List all skills, optionally filtered by category."""
        if category:
            return [s for s in self._skills.values() if s.category == category]
        return list(self._skills.values())

    def get_skill_context(self, skill_ids: Optional[List[str]] = None) -> str:
        """Build context string from skills for prompt injection.

        Args:
            skill_ids: Specific skills to include. None = all skills.

        Returns:
            Formatted context string.
        """
        skills = (
            [self._skills[sid] for sid in skill_ids if sid in self._skills]
            if skill_ids
            else list(self._skills.values())
        )

        if not skills:
            return ""

        parts = ["--- Agent Skills (企業知識) ---"]
        for skill in skills:
            parts.append(f"\n### {skill.name}")
            parts.append(skill.content)
        parts.append("\n--- Agent Skills 結束 ---")
        return "\n".join(parts)

    def search_skills(self, query: str, limit: int = 3) -> List[AgentSkill]:
        """Simple keyword search across skills."""
        query_lower = query.lower()
        scored: List[tuple] = []
        for skill in self._skills.values():
            score = 0
            searchable = f"{skill.name} {skill.description} {' '.join(skill.tags)} {skill.content}".lower()
            for word in query_lower.split():
                if word in searchable:
                    score += 1
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]
