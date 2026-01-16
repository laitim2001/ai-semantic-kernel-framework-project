# IPA Platform 架構增強：Input Gateway Layer

> **版本**: 1.0  
> **日期**: 2026-01-15  
> **狀態**: 架構設計  
> **目的**: 在 MAF 編排層之前增加輸入管理層，確保進入核心流程的請求都是「可處理的」

---

## 一、問題陳述

### 1.1 當前架構的盲點

```
當前流程:
═════════

ServiceNow ──┐
Teams Bot ───┼──▶ Event Ingestion API ──▶ MAF Orchestrator ──▶ Intent Router ──▶ ...
Prometheus ──┘         (只做排隊)            (假設輸入可處理)

問題:
═════
當 Teams Bot 收到「系統好像有點問題」時：
1. Event Ingestion API 無法判斷這是否足夠
2. 直接進入 MAF Orchestrator
3. Intent Router 識別為 incident
4. 但資訊不足，無法執行有意義的診斷
5. 只能在 Workflow 中間來回詢問用戶
6. 用戶體驗差，處理效率低
```

### 1.2 根本原因

| 來源類型 | 資料品質 | 當前處理 | 問題 |
|---------|---------|---------|------|
| ServiceNow Webhook | 結構化、完整 | 直接入隊 | ✅ 無問題 |
| Prometheus Alert | 結構化、完整 | 直接入隊 | ✅ 無問題 |
| **Teams Bot** | **自由文本、可能不完整** | 直接入隊 | ❌ 問題源頭 |
| **Chat UI** | **自由文本、可能不完整** | 直接入隊 | ❌ 問題源頭 |

---

## 二、解決方案：Input Gateway Layer

### 2.1 設計理念

```
核心原則:
═════════
「在入口點就控制輸入品質，而不是在流程中間來回補救」

實現方式:
═════════
根據來源類型採用不同的入口策略：
• 系統來源 → Schema 驗證 + 標準化 → 直接入隊
• 用戶來源 → Conversation Gateway → 引導式對話 → 達標後入隊
```

### 2.2 更新後的完整架構

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           企業 IT 事件智能處理平台 (更新版)                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ╔═══════════════════════════════════════════════════════════════════════════════╗  │
│  ║                         Layer 0: Input Gateway (新增) ⭐                       ║  │
│  ╠═══════════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                                ║  │
│  ║   系統來源 (Structured)                   用戶來源 (Unstructured)             ║  │
│  ║   ═══════════════════════                 ═══════════════════════             ║  │
│  ║                                                                                ║  │
│  ║   ┌─────────────┐                         ┌─────────────┐                     ║  │
│  ║   │ ServiceNow  │                         │   Teams     │                     ║  │
│  ║   │  Webhook    │                         │    Bot      │                     ║  │
│  ║   └──────┬──────┘                         └──────┬──────┘                     ║  │
│  ║          │                                       │                             ║  │
│  ║   ┌─────────────┐                         ┌─────────────┐                     ║  │
│  ║   │ Prometheus  │                         │   Slack     │                     ║  │
│  ║   │   Alert     │                         │    Bot      │                     ║  │
│  ║   └──────┬──────┘                         └──────┬──────┘                     ║  │
│  ║          │                                       │                             ║  │
│  ║          ▼                                       ▼                             ║  │
│  ║   ┌─────────────────────┐              ┌─────────────────────────────────┐    ║  │
│  ║   │ Schema Validator    │              │   Conversation Gateway          │    ║  │
│  ║   │                     │              │                                 │    ║  │
│  ║   │ • 驗證必要欄位      │              │  ┌─────────────────────────┐   │    ║  │
│  ║   │ • 資料型別檢查      │              │  │  Intent Pre-classifier  │   │    ║  │
│  ║   │ • 標準化格式        │              │  │  (輕量級意圖預判)       │   │    ║  │
│  ║   │                     │              │  └───────────┬─────────────┘   │    ║  │
│  ║   │ 驗證通過? ─────┐    │              │              │                 │    ║  │
│  ║   │   Yes → 入隊   │    │              │              ▼                 │    ║  │
│  ║   │   No → 拒絕    │    │              │  ┌─────────────────────────┐   │    ║  │
│  ║   └────────────────┼────┘              │  │ Completeness Checker    │   │    ║  │
│  ║                    │                   │  │ (資訊完整度檢查)        │   │    ║  │
│  ║                    │                   │  └───────────┬─────────────┘   │    ║  │
│  ║                    │                   │              │                 │    ║  │
│  ║                    │                   │       ┌──────┴──────┐         │    ║  │
│  ║                    │                   │       │             │         │    ║  │
│  ║                    │                   │       ▼             ▼         │    ║  │
│  ║                    │                   │   >= 60%        < 60%        │    ║  │
│  ║                    │                   │   完整度        完整度       │    ║  │
│  ║                    │                   │       │             │         │    ║  │
│  ║                    │                   │       │             ▼         │    ║  │
│  ║                    │                   │       │   ┌─────────────────┐ │    ║  │
│  ║                    │                   │       │   │ Guided Dialog   │ │    ║  │
│  ║                    │                   │       │   │ (引導式對話)    │ │    ║  │
│  ║                    │                   │       │   │                 │ │    ║  │
│  ║                    │                   │       │   │ • 智能提問      │ │    ║  │
│  ║                    │                   │       │   │ • 快速選項      │ │    ║  │
│  ║                    │                   │       │   │ • 上下文保持    │ │    ║  │
│  ║                    │                   │       │   └────────┬────────┘ │    ║  │
│  ║                    │                   │       │            │          │    ║  │
│  ║                    │                   │       │    (達標後) │          │    ║  │
│  ║                    │                   │       │◀───────────┘          │    ║  │
│  ║                    │                   │       │                        │    ║  │
│  ║                    │                   └───────┼────────────────────────┘    ║  │
│  ║                    │                           │                             ║  │
│  ║                    └───────────────────────────┤                             ║  │
│  ║                                                │                             ║  │
│  ║                                                ▼                             ║  │
│  ║                         ┌──────────────────────────────────────────┐         ║  │
│  ║                         │         Normalized Request Queue         │         ║  │
│  ║                         │                                          │         ║  │
│  ║                         │  所有請求都是「可處理的」：              │         ║  │
│  ║                         │  • 有明確的意圖                          │         ║  │
│  ║                         │  • 有足夠的上下文                        │         ║  │
│  ║                         │  • 有標準化的格式                        │         ║  │
│  ║                         └──────────────────────┬───────────────────┘         ║  │
│  ╚════════════════════════════════════════════════│═══════════════════════════════╝  │
│                                                   │                                   │
│                                                   ▼                                   │
│  ╔════════════════════════════════════════════════════════════════════════════════╗  │
│  ║                              Layer 1: MAF 編排層 (原 Layer 3)                   ║  │
│  ╠════════════════════════════════════════════════════════════════════════════════╣  │
│  ║                                                                                 ║  │
│  ║   ┌─────────────────────────────────────────────────────────────────────────┐  ║  │
│  ║   │                     MAF Orchestrator Service                            │  ║  │
│  ║   │                                                                         │  ║  │
│  ║   │   現在可以假設：                                                        │  ║  │
│  ║   │   • 輸入已經過預分類                                                    │  ║  │
│  ║   │   • 必要資訊已收集                                                      │  ║  │
│  ║   │   • 格式已標準化                                                        │  ║  │
│  ║   │                                                                         │  ║  │
│  ║   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  ║  │
│  ║   │   │Intent Router │  │ Risk Assessor│  │ HITL Manager │                 │  ║  │
│  ║   │   │(精細分類)    │  │ (風險評估)   │  │ (人機協作)   │                 │  ║  │
│  ║   │   └──────────────┘  └──────────────┘  └──────────────┘                 │  ║  │
│  ║   │                                                                         │  ║  │
│  ║   │   Intent Router 的職責變化:                                            │  ║  │
│  ║   │   • 之前: 從零開始識別意圖 + 處理模糊輸入                              │  ║  │
│  ║   │   • 現在: 細化已預分類的意圖 + 選擇工作流                              │  ║  │
│  ║   │                                                                         │  ║  │
│  ║   └─────────────────────────────────────────────────────────────────────────┘  ║  │
│  ╚════════════════════════════════════════════════════════════════════════════════╝  │
│                                                                                       │
│  (後續層級保持不變...)                                                               │
│                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、Conversation Gateway 詳細設計

### 3.1 組件職責

| 組件 | 職責 | 說明 |
|------|------|------|
| **Intent Pre-classifier** | 快速意圖預判 | 使用輕量級模型/規則判斷大類 |
| **Completeness Checker** | 資訊完整度評估 | 根據意圖類型檢查必要欄位 |
| **Guided Dialog** | 引導式對話 | 智能提問，收集缺失資訊 |
| **Context Manager** | 上下文管理 | 多輪對話狀態保持 |

### 3.2 處理流程

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     Conversation Gateway 處理流程                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   用戶: "系統好像有點問題"                                                          │
│           │                                                                          │
│           ▼                                                                          │
│   ┌───────────────────────────────────────────────────────────────────────────┐     │
│   │ Step 1: Intent Pre-classifier                                             │     │
│   │                                                                           │     │
│   │ 使用輕量級方法快速判斷意圖大類:                                           │     │
│   │ • 方法: 關鍵字 + 簡單 embedding                                          │     │
│   │ • 不需要精確，只需判斷大方向                                              │     │
│   │ • 延遲要求: < 100ms                                                       │     │
│   │                                                                           │     │
│   │ 結果: category = "incident" (可信度 0.75)                                 │     │
│   └───────────────────────────────────────────────────────────────────────────┘     │
│           │                                                                          │
│           ▼                                                                          │
│   ┌───────────────────────────────────────────────────────────────────────────┐     │
│   │ Step 2: Completeness Checker                                              │     │
│   │                                                                           │     │
│   │ 對於 incident 類型，必要欄位:                                             │     │
│   │ ┌─────────────────────────────────────────────────────────────────────┐  │     │
│   │ │  Field              Required   Provided   Status                    │  │     │
│   │ │  ─────────────────────────────────────────────────────────────────  │  │     │
│   │ │  affected_system    Yes        No         ❌ 缺失                   │  │     │
│   │ │  symptom_type       Yes        Partial    ⚠️ "有點問題" 太模糊      │  │     │
│   │ │  severity_hint      No         No         - 可選                    │  │     │
│   │ │  start_time         No         No         - 可選                    │  │     │
│   │ │  affected_users     No         No         - 可選                    │  │     │
│   │ │  error_message      No         No         - 可選                    │  │     │
│   │ └─────────────────────────────────────────────────────────────────────┘  │     │
│   │                                                                           │     │
│   │ 完整度: 15%  (閾值: 60%)                                                  │     │
│   │ 判定: 需要引導對話                                                        │     │
│   └───────────────────────────────────────────────────────────────────────────┘     │
│           │                                                                          │
│           ▼                                                                          │
│   ┌───────────────────────────────────────────────────────────────────────────┐     │
│   │ Step 3: Guided Dialog                                                     │     │
│   │                                                                           │     │
│   │ 生成最高效的問題 (一次最多 2-3 個):                                       │     │
│   │                                                                           │     │
│   │ 系統回覆:                                                                 │     │
│   │ ┌─────────────────────────────────────────────────────────────────────┐  │     │
│   │ │  "我來幫你處理這個問題。請先告訴我：                                │  │     │
│   │ │                                                                     │  │     │
│   │ │   1️⃣ 是哪個系統有問題？                                            │  │     │
│   │ │      [ETL/報表] [ERP/D365] [郵件] [網站] [其他]                     │  │     │
│   │ │                                                                     │  │     │
│   │ │   2️⃣ 具體是什麼情況？                                              │  │     │
│   │ │      [很慢] [報錯] [無法登入] [數據不對] [完全不能用]               │  │     │
│   │ │                                                                     │  │     │
│   │ │   或者你可以直接描述更多細節。"                                     │  │     │
│   │ └─────────────────────────────────────────────────────────────────────┘  │     │
│   └───────────────────────────────────────────────────────────────────────────┘     │
│           │                                                                          │
│           │  用戶點擊: [ETL/報表] [報錯]                                            │
│           ▼                                                                          │
│   ┌───────────────────────────────────────────────────────────────────────────┐     │
│   │ Step 4: 更新完整度                                                        │     │
│   │                                                                           │     │
│   │ ┌─────────────────────────────────────────────────────────────────────┐  │     │
│   │ │  Field              Required   Provided   Status                    │  │     │
│   │ │  ─────────────────────────────────────────────────────────────────  │  │     │
│   │ │  affected_system    Yes        Yes        ✅ "ETL/報表"             │  │     │
│   │ │  symptom_type       Yes        Yes        ✅ "報錯"                 │  │     │
│   │ │  severity_hint      No         No         - 可選                    │  │     │
│   │ │  start_time         No         No         - 可選                    │  │     │
│   │ │  affected_users     No         No         - 可選                    │  │     │
│   │ │  error_message      No         No         - 可選                    │  │     │
│   │ └─────────────────────────────────────────────────────────────────────┘  │     │
│   │                                                                           │     │
│   │ 完整度: 70%  ✅ (>= 閾值 60%)                                             │     │
│   │ 判定: 可以進入 MAF 編排層                                                 │     │
│   └───────────────────────────────────────────────────────────────────────────┘     │
│           │                                                                          │
│           ▼                                                                          │
│   ┌───────────────────────────────────────────────────────────────────────────┐     │
│   │ Step 5: 構建 Normalized Request                                           │     │
│   │                                                                           │     │
│   │ {                                                                         │     │
│   │   "request_id": "REQ-2026-0115-001",                                     │     │
│   │   "source": "teams_bot",                                                 │     │
│   │   "source_type": "user_conversation",                                    │     │
│   │   "user_id": "chris.lai@ricoh.com",                                      │     │
│   │   "conversation_id": "conv_abc123",                                      │     │
│   │                                                                           │     │
│   │   "pre_classification": {                                                │     │
│   │     "intent_category": "incident",                                       │     │
│   │     "confidence": 0.85                                                   │     │
│   │   },                                                                      │     │
│   │                                                                           │     │
│   │   "collected_info": {                                                    │     │
│   │     "affected_system": "ETL/報表",                                       │     │
│   │     "symptom_type": "報錯",                                              │     │
│   │     "original_text": "系統好像有點問題",                                 │     │
│   │     "completeness_score": 0.70                                           │     │
│   │   },                                                                      │     │
│   │                                                                           │     │
│   │   "conversation_context": {                                              │     │
│   │     "turns": 2,                                                          │     │
│   │     "duration_seconds": 15                                               │     │
│   │   }                                                                       │     │
│   │ }                                                                         │     │
│   │                                                                           │     │
│   │ ──▶ 發送到 Normalized Request Queue ──▶ MAF Orchestrator                 │     │
│   └───────────────────────────────────────────────────────────────────────────┘     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 完整度定義 (按意圖類型)

```python
# /src/input_gateway/completeness_rules.py

COMPLETENESS_RULES = {
    "incident": {
        "required": {
            "affected_system": {
                "weight": 0.4,
                "question": "是哪個系統有問題？",
                "options": ["ETL/報表", "ERP/D365", "郵件", "網站", "VPN", "其他"]
            },
            "symptom_type": {
                "weight": 0.3,
                "question": "具體是什麼情況？",
                "options": ["很慢", "報錯", "無法登入", "數據不對", "完全不能用"]
            }
        },
        "optional": {
            "severity_hint": {
                "weight": 0.1,
                "question": "影響程度？",
                "options": ["只影響我", "影響團隊", "影響部門", "影響全公司"]
            },
            "start_time": {
                "weight": 0.1,
                "question": "什麼時候開始的？",
                "options": ["剛剛", "今天", "昨天", "更早"]
            },
            "error_message": {
                "weight": 0.1,
                "question": "有看到什麼錯誤訊息嗎？",
                "options": null  # 自由輸入
            }
        },
        "threshold": 0.60  # 至少需要 60% 完整度
    },
    
    "request": {
        "required": {
            "request_type": {
                "weight": 0.4,
                "question": "你需要什麼服務？",
                "options": ["帳號申請", "權限變更", "軟體安裝", "硬體需求", "其他"]
            },
            "target": {
                "weight": 0.3,
                "question": "針對什麼系統或資源？",
                "options": ["ERP", "郵件", "VPN", "共享資料夾", "其他"]
            }
        },
        "optional": {
            "justification": {
                "weight": 0.2,
                "question": "申請原因是？",
                "options": null
            },
            "urgency": {
                "weight": 0.1,
                "question": "緊急程度？",
                "options": ["一般", "急", "非常急"]
            }
        },
        "threshold": 0.60
    },
    
    "change": {
        "required": {
            "change_type": {
                "weight": 0.3,
                "question": "什麼類型的變更？",
                "options": ["部署", "配置變更", "資料更新", "維護", "其他"]
            },
            "target_system": {
                "weight": 0.3,
                "question": "變更哪個系統？",
                "options": ["ETL", "ERP", "網站", "資料庫", "其他"]
            },
            "environment": {
                "weight": 0.2,
                "question": "哪個環境？",
                "options": ["開發", "測試", "UAT", "生產"]
            }
        },
        "optional": {
            "schedule": {
                "weight": 0.2,
                "question": "預計何時進行？",
                "options": ["現在", "今天", "本週", "下週", "待定"]
            }
        },
        "threshold": 0.70  # 變更類型需要更高完整度
    },
    
    "query": {
        "required": {
            "query_target": {
                "weight": 0.5,
                "question": "你想查詢什麼？",
                "options": ["系統狀態", "數據/報表", "日誌", "設定", "其他"]
            }
        },
        "optional": {
            "time_range": {
                "weight": 0.3,
                "question": "時間範圍？",
                "options": ["今天", "本週", "本月", "自定義"]
            },
            "format": {
                "weight": 0.2,
                "question": "需要什麼格式？",
                "options": ["簡單回答", "詳細報告", "Excel", "圖表"]
            }
        },
        "threshold": 0.50  # 查詢類型完整度要求較低
    }
}
```

---

## 四、設計決策說明

### 4.1 為什麼在 MAF 編排層「之前」處理？

| 方案 | 優點 | 缺點 |
|------|------|------|
| **方案 A: 在 Intent Router 之後澄清** | 意圖已確定，問題更精確 | 已進入核心流程，來回成本高 |
| **方案 B: 在入口處澄清 ✅** | 控制輸入品質，核心流程更簡潔 | 需要額外組件 |

選擇方案 B 的原因：
1. **關注點分離**：輸入管理和業務邏輯分離
2. **效率**：避免在 Workflow 中間暫停等待用戶
3. **用戶體驗**：用戶知道「先回答問題，再處理」是合理的

### 4.2 Intent Pre-classifier vs Intent Router

| 組件 | 位置 | 目的 | 精確度要求 | 方法 |
|------|------|------|-----------|------|
| **Intent Pre-classifier** | Input Gateway | 判斷意圖大類，決定收集什麼資訊 | 中等 (75%+) | 關鍵字 + 輕量 embedding |
| **Intent Router** | MAF 編排層 | 精確分類，選擇工作流 | 高 (95%+) | 三層路由架構 |

```
分工:
═════

Pre-classifier: "這是一個 incident"  (粗分類)
        ↓
  收集 incident 需要的資訊
        ↓
Intent Router: "這是 etl_failure，需要 magentic workflow"  (細分類)
```

### 4.3 完整度閾值的考量

| 閾值 | 效果 | 適用場景 |
|------|------|---------|
| **過低 (< 50%)** | 收集太少資訊，後續仍需來回 | ❌ 不建議 |
| **適中 (60-70%)** | 平衡效率和用戶耐心 | ✅ 一般場景 |
| **過高 (> 80%)** | 用戶需要回答太多問題 | ⚠️ 僅限高風險操作 |

---

## 五、系統來源 vs 用戶來源處理差異

### 5.1 系統來源處理

```python
# /src/input_gateway/system_source_handler.py

class SystemSourceHandler:
    """
    處理來自系統的結構化輸入
    """
    
    def __init__(self):
        self.schemas = {
            "servicenow": ServiceNowSchema,
            "prometheus": PrometheusAlertSchema,
            "defender": DefenderAlertSchema
        }
    
    async def process(self, source: str, payload: dict) -> NormalizedRequest:
        """
        驗證並標準化系統輸入
        """
        schema = self.schemas.get(source)
        if not schema:
            raise ValueError(f"Unknown source: {source}")
        
        # 1. Schema 驗證
        validated = schema.validate(payload)
        
        # 2. 標準化
        normalized = NormalizedRequest(
            request_id=generate_id(),
            source=source,
            source_type="system",
            
            # 系統來源直接信任預分類
            pre_classification={
                "intent_category": self._map_to_intent(source, validated),
                "confidence": 0.95  # 系統來源高信心度
            },
            
            # 直接使用結構化數據
            collected_info=validated,
            completeness_score=1.0  # 系統來源假設完整
        )
        
        return normalized
    
    def _map_to_intent(self, source: str, data: dict) -> str:
        """
        根據來源和數據映射到意圖
        """
        mappings = {
            "servicenow": {
                "incident": "incident",
                "request": "request",
                "change": "change"
            },
            "prometheus": {
                "alert": "incident"
            },
            "defender": {
                "alert": "incident"
            }
        }
        return mappings[source].get(data.get("type"), "unknown")


# ServiceNow Webhook 格式
class ServiceNowSchema:
    """
    ServiceNow 已經提供完整結構化數據
    """
    required_fields = [
        "number",       # INC0012345
        "short_description",
        "category",     # incident | request | change
        "priority",
        "caller_id",
        "assignment_group"
    ]
    
    @classmethod
    def validate(cls, payload: dict) -> dict:
        for field in cls.required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")
        return payload
```

### 5.2 用戶來源處理

```python
# /src/input_gateway/conversation_gateway.py

class ConversationGateway:
    """
    處理來自用戶的非結構化輸入
    """
    
    def __init__(self):
        self.pre_classifier = IntentPreClassifier()
        self.completeness_checker = CompletenessChecker()
        self.dialog_generator = GuidedDialogGenerator()
        self.context_manager = ConversationContextManager()
    
    async def process(
        self, 
        user_id: str, 
        message: str,
        conversation_id: str = None
    ) -> Union[NormalizedRequest, DialogResponse]:
        """
        處理用戶訊息
        
        Returns:
            NormalizedRequest: 如果資訊足夠，返回標準化請求
            DialogResponse: 如果資訊不足，返回引導對話
        """
        
        # 1. 獲取或創建對話上下文
        context = await self.context_manager.get_or_create(
            user_id, conversation_id
        )
        
        # 2. 更新上下文
        context.add_user_message(message)
        
        # 3. 意圖預分類 (如果還沒有)
        if not context.intent_category:
            pre_class = await self.pre_classifier.classify(
                context.get_full_conversation()
            )
            context.intent_category = pre_class.category
            context.intent_confidence = pre_class.confidence
        
        # 4. 從對話中提取資訊
        extracted = await self._extract_info(context)
        context.update_collected_info(extracted)
        
        # 5. 檢查完整度
        completeness = self.completeness_checker.check(
            context.intent_category,
            context.collected_info
        )
        
        # 6. 判斷是否足夠
        if completeness.score >= completeness.threshold:
            # 足夠了！構建 NormalizedRequest
            return self._build_normalized_request(context)
        else:
            # 不夠，生成引導對話
            dialog = self.dialog_generator.generate(
                intent=context.intent_category,
                collected=context.collected_info,
                missing=completeness.missing_fields
            )
            
            # 保存上下文
            await self.context_manager.save(context)
            
            return DialogResponse(
                conversation_id=context.conversation_id,
                message=dialog.message,
                quick_options=dialog.options,
                completeness_score=completeness.score
            )
    
    async def _extract_info(self, context: ConversationContext) -> dict:
        """
        從對話中提取結構化資訊
        使用 Claude Haiku 進行輕量級提取
        """
        prompt = f"""
        從以下對話中提取資訊：
        
        {context.get_full_conversation()}
        
        需要提取的欄位（根據意圖類型 {context.intent_category}）：
        {COMPLETENESS_RULES[context.intent_category]}
        
        以 JSON 格式輸出已識別的欄位值。
        """
        
        response = await self.haiku_client.extract(prompt)
        return response.extracted_fields
```

---

## 六、與現有架構的整合

### 6.1 更新後的層級定義

| 層級 | 原名稱 | 新名稱 | 職責變化 |
|------|--------|--------|---------|
| **Layer 0** | (新增) | **Input Gateway** | 輸入管理、品質控制 |
| Layer 1 | 入口層 | 整合到 Layer 0 | - |
| Layer 2 | 前端展示層 | 保持不變 | - |
| **Layer 3** | MAF 編排層 | 保持不變 | 假設輸入已標準化 |
| Layer 4 | Claude Worker | 保持不變 | - |
| Layer 5 | MCP 工具層 | 保持不變 | - |

### 6.2 組件責任對比

| 組件 | 原職責 | 新職責 |
|------|--------|--------|
| **Event Ingestion API** | 接收所有輸入 | 只接收系統來源 |
| **Conversation Gateway** | (新增) | 處理用戶來源 |
| **Intent Router** | 從零識別意圖 | 細化預分類結果 |
| **Risk Assessor** | 保持不變 | 保持不變 |
| **HITL Manager** | 保持不變 | 保持不變 |

---

## 七、實施建議

### 7.1 分階段實施

```
Phase A: 基礎設施 (1 週)
═══════════════════════
• 創建 Input Gateway 服務骨架
• 定義 Normalized Request 格式
• 設置系統來源和用戶來源的路由

Phase B: 系統來源處理 (1 週)
═══════════════════════════
• 實現 Schema Validator
• 整合現有 ServiceNow webhook
• 整合 Prometheus alert

Phase C: 用戶來源處理 (2 週)
═══════════════════════════
• 實現 Intent Pre-classifier
• 實現 Completeness Checker
• 實現 Guided Dialog Generator
• 實現 Conversation Context Manager

Phase D: 整合測試 (1 週)
═══════════════════════
• 端到端測試
• 用戶體驗測試
• 性能測試
```

### 7.2 關鍵指標

| 指標 | 目標 | 說明 |
|------|------|------|
| 平均對話輪數 | < 3 | 用戶平均需要回答幾輪問題 |
| 首次完整率 | > 30% | 用戶第一次輸入就足夠的比例 |
| 放棄率 | < 10% | 用戶在對話中途放棄的比例 |
| Gateway 延遲 | < 200ms | 每輪對話的處理時間 |

---

## 八、總結

### 8.1 架構改進

```
之前:
═════
所有輸入 → Event Ingestion → MAF Orchestrator → 可能需要來回澄清

現在:
═════
系統輸入 → Schema Validator → Normalized Queue → MAF Orchestrator (資訊完整)
                                      ↑
用戶輸入 → Conversation Gateway ──────┘
           (確保資訊足夠才放行)
```

### 8.2 核心價值

| 改進 | 效果 |
|------|------|
| **用戶體驗** | 清晰的對話流程，而非在處理中被打斷 |
| **處理效率** | MAF 編排層收到的都是可處理的請求 |
| **架構清晰** | 輸入管理和業務邏輯分離 |
| **可維護性** | 不同來源的處理邏輯獨立 |

---

**文件結束**