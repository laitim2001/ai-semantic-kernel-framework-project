# 智能體架構中的 Context Window 管理策略

> **文件版本**: 1.0
> **創建日期**: 2026-01-28
> **分析基礎**: V2 架構文件 + 代碼審計 + 業界最佳實踐
> **關聯文件**: `MAF-Claude-Hybrid-Architecture-V2.md`, `MAF-Features-Architecture-Mapping-V2.md`

---

## 執行摘要

本文件深入探討在 Microsoft Agent Framework (MAF) 智能體集群架構中，如何有效管理 Context Window（上下文窗口）限制。主要解決三個核心問題：

1. **識別限制**: 如何偵測對話何時接近或超過上下文窗口限制？
2. **控制策略**: 如何自動或手動控制上下文大小？
3. **長期對話**: 如何在智能體集群場景下實現持續的長時間對話？

### 關鍵結論

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Context Window 管理架構總覽                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─── 識別層 (Detection) ──────────────────────────────────────────────┐    │
│  │  Token Counter → Threshold Monitor → Alert System                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                              │                                             │
│                              ▼                                             │
│  ┌─── 控制層 (Control) ────────────────────────────────────────────────┐    │
│  │  策略選擇 → 壓縮引擎 → 摘要生成 → Context 重構                       │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                              │                                             │
│                              ▼                                             │
│  ┌─── 持久層 (Persistence) ────────────────────────────────────────────┐    │
│  │  MAF Checkpoint ⇄ Context Bridge ⇄ 三層記憶系統                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  實現長期對話的關鍵：                                                        │
│  ① Token 使用量追蹤與閾值告警                                               │
│  ② 智能壓縮策略（保留關鍵、摘要次要、丟棄冗餘）                            │
│  ③ MAF Checkpoint 與記憶系統深度整合                                        │
│  ④ 跨 Agent 上下文橋接與同步                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 第一部分：問題定義與業界實踐

### 1.1 Context Window 限制的本質

```
Context Window = 模型能夠「看見」的全部信息窗口
═══════════════════════════════════════════════

Claude 3.5 Sonnet: 200K tokens
Claude 3 Opus:     200K tokens
GPT-4o:            128K tokens
Azure OpenAI:      128K tokens (視部署而定)

但是，有效上下文 ≠ 最大上下文

┌─────────────────────────────────────────────────┐
│  有效上下文分配 (以 128K 為例)                    │
├─────────────────────────────────────────────────┤
│  System Prompt        │   8K  │  6.25%         │
│  Tools Definition     │   4K  │  3.125%        │
│  Conversation History │  80K  │  62.5%  ← 主要 │
│  Current Input        │  16K  │  12.5%         │
│  Reserved for Output  │  20K  │  15.625%       │
└─────────────────────────────────────────────────┘

實際可用於對話歷史的空間約為總容量的 50-70%
```

### 1.2 智能體集群的特殊挑戰

與單一聊天機器人不同，智能體集群面臨額外複雜性：

| 挑戰 | 描述 | 影響 |
|------|------|------|
| **多 Agent 狀態** | 每個 Agent 維護自己的上下文 | 總體記憶體消耗倍增 |
| **Handoff 上下文傳遞** | Agent 間需要傳遞完整上下文 | 傳遞的資訊可能很大 |
| **GroupChat 討論** | 多個 Agent 的對話歷史交織 | 歷史增長速度加快 |
| **工具調用記錄** | 每次工具調用都佔用上下文 | 複雜任務快速消耗配額 |
| **MAF 狀態同步** | MAF 和 Claude 狀態需雙向同步 | 同步過程有重複資訊 |

### 1.3 業界工具的做法對比

| 工具 | Context 管理策略 | 長期對話方案 |
|------|-----------------|--------------|
| **Claude Code** | Auto-compact + 手動 /compact | 自動摘要歷史對話 |
| **OpenAI Codex** | 滑動窗口 + 摘要 | API 不保留歷史 |
| **Cursor** | Smart context + 代碼片段 | 選擇性包含檔案 |
| **GitHub Copilot** | 局部上下文（當前檔案周圍） | 無持久記憶 |
| **IPA Platform** | 三層記憶 + MAF Checkpoint | 分層持久化 + 摘要 |

---

## 第二部分：IPA Platform 現有架構分析

### 2.1 現有 Context Window 管理機制

IPA Platform 已經實現了相當成熟的上下文管理系統：

```
現有架構 (backend/src/integrations/)
═══════════════════════════════════

memory/
├── unified_memory.py       → 三層記憶管理器
├── mem0_client.py          → 長期記憶 (向量存儲)
├── embeddings.py           → 嵌入向量服務
└── utils.py                → 記憶工具函數

hybrid/
├── context/
│   ├── bridge.py           → MAF ⇄ Claude 上下文橋接
│   ├── mapper.py           → 上下文格式映射
│   └── sync/
│       ├── synchronizer.py → 同步引擎
│       └── conflict_resolver.py → 衝突解決
├── checkpoint/
│   ├── storage.py          → Checkpoint 存儲抽象
│   ├── backends/           → 4 種存儲後端
│   │   ├── memory.py       → 開發用
│   │   ├── redis.py        → 生產推薦
│   │   ├── postgres.py     → 合規需求
│   │   └── filesystem.py   → 備用
│   └── hybrid_checkpoint.py → 統一 Checkpoint 管理

claude_sdk/
├── session_state.py        → 會話狀態管理
├── orchestrator/
│   └── context_manager.py  → 多 Agent 上下文協調
└── multiturn/
    └── adapter.py          → 多輪對話適配器
```

### 2.2 三層記憶系統詳解

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  三層記憶架構 (UnifiedMemoryManager)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─── Layer 1: Working Memory (工作記憶) ──────────────────────────────────┐ │
│  │  存儲: Redis                                                            │ │
│  │  TTL:  30 分鐘                                                          │ │
│  │  速度: < 10ms                                                           │ │
│  │  容量: ~5MB per session                                                 │ │
│  │                                                                          │ │
│  │  用途: 當前對話的即時上下文                                              │ │
│  │        • 最近的對話歷史                                                  │ │
│  │        • 工具調用的臨時結果                                              │ │
│  │        • Agent 中間狀態                                                  │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                              │ (重要性 > 0.5 時晉升)                          │
│                              ▼                                              │
│  ┌─── Layer 2: Session Memory (會話記憶) ──────────────────────────────────┐ │
│  │  存儲: PostgreSQL / Redis                                               │ │
│  │  TTL:  7 天                                                             │ │
│  │  速度: < 100ms                                                          │ │
│  │  容量: ~50MB per session                                                │ │
│  │                                                                          │ │
│  │  用途: 會話級別的完整歷史                                                │ │
│  │        • 完整對話歷史（壓縮存儲）                                        │ │
│  │        • Checkpoint 數據                                                │ │
│  │        • 決策追蹤記錄                                                    │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                              │ (重要性 > 0.8 或特定類型時晉升)                 │
│                              ▼                                              │
│  ┌─── Layer 3: Long-term Memory (長期記憶) ────────────────────────────────┐ │
│  │  存儲: mem0 + Qdrant (向量資料庫)                                        │ │
│  │  TTL:  永久                                                             │ │
│  │  速度: < 1000ms                                                         │ │
│  │  容量: 無限制                                                           │ │
│  │                                                                          │ │
│  │  用途: 跨會話的知識累積                                                  │ │
│  │        • 已解決問題的案例                                                │ │
│  │        • 學習到的最佳實踐                                                │ │
│  │        • 使用者偏好和模式                                                │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  記憶晉升邏輯 (位於 unified_memory.py):                                       │
│  ────────────────────────────────────                                        │
│  if importance >= 0.8:                                                       │
│      return MemoryLayer.LONG_TERM                                            │
│  if memory_type in [EVENT_RESOLUTION, BEST_PRACTICE]:                        │
│      return MemoryLayer.LONG_TERM                                            │
│  if memory_type == CONVERSATION:                                             │
│      if importance >= 0.5:                                                   │
│          return MemoryLayer.SESSION                                          │
│      return MemoryLayer.WORKING                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 現有壓縮機制

```python
# 位置: claude_sdk/session_state.py

class SessionStateConfig:
    max_context_tokens: int = 10000              # Context 上限
    preserve_recent_messages: int = 10           # 保留最近 N 條
    context_summarization_enabled: bool = True   # 啟用摘要
    compression_threshold: int = 1000            # 壓縮閾值

# 壓縮策略 (三層遞進):

策略 1: 保留最近消息
────────────────────
messages = messages[-preserve_recent_messages:]

策略 2: 摘要舊消息
────────────────────
if context_summarization_enabled:
    summary = f"[Summary of {len(old_messages)} messages: ...]"
    messages = [summary_message] + recent_messages

策略 3: 壓縮大型上下文項
────────────────────────
for key, value in context.items():
    if len(str(value)) > 500:
        context[key] = f"[Compressed: {len(str(value))} chars]"
```

### 2.4 MAF Checkpoint 整合

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MAF Checkpoint 與 Context 整合架構                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  HybridCheckpoint (hybrid_checkpoint.py)                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  MAFCheckpointState                 ClaudeCheckpointState             │    │
│  │  ├─ workflow_id                     ├─ session_id                     │    │
│  │  ├─ current_step                    ├─ context_variables              │    │
│  │  ├─ agent_states: Dict              ├─ conversation_history           │    │
│  │  ├─ execution_records: List         ├─ tool_call_history              │    │
│  │  ├─ pending_approvals: List         ├─ is_compressed: bool            │    │
│  │  └─ checkpoint_data: bytes          └─ total_tokens: int              │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  ContextBridge.sync()                                                 │    │
│  │                                                                        │    │
│  │  MAF → Claude:                     Claude → MAF:                       │    │
│  │  ─────────────                     ─────────────                       │    │
│  │  workflow_id → session_id          context_vars → checkpoint_data     │    │
│  │  checkpoint_data → context_vars    history → execution_records        │    │
│  │  exec_history → conversation       tool_calls → checkpoint updates    │    │
│  │  agent_states → system_prompt      (衝突解決策略)                     │    │
│  │  approvals → tool_call_history                                        │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Checkpoint 觸發時機:                                                         │
│  ──────────────────                                                          │
│  • AUTO: 每 5 輪對話自動保存                                                 │
│  • MANUAL: 用戶/系統主動請求                                                 │
│  • MODE_SWITCH: MAF ⇄ Claude 切換時                                         │
│  • HITL: 進入人工審批等待時                                                  │
│  • RECOVERY: 錯誤恢復前                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 第三部分：識別 Context Window 限制的方法

### 3.1 Token 計數策略

```python
# 推薦實現方案 (新增功能)

class TokenCounter:
    """多模型 Token 計數器"""

    # 方法 1: 精確計數 (使用 tiktoken)
    def count_exact(self, text: str, model: str = "claude-3") -> int:
        """精確計數，但速度較慢"""
        if model.startswith("claude"):
            # Claude 沒有官方 tokenizer，使用 Anthropic 的估算 API
            # 或使用近似計算
            return self._estimate_claude_tokens(text)
        elif model.startswith("gpt"):
            import tiktoken
            enc = tiktoken.encoding_for_model(model)
            return len(enc.encode(text))
        return len(text) // 4  # 粗略估計

    # 方法 2: 快速估算 (即時監控用)
    def count_fast(self, text: str) -> int:
        """快速估算，4 字符 = 1 token"""
        # 中文約 1.5-2 字符 = 1 token
        # 英文約 4 字符 = 1 token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    # 方法 3: 分段計數 (對話管理用)
    def count_messages(self, messages: List[Message]) -> Dict[str, int]:
        """分段計數，返回各部分 token 使用量"""
        result = {
            "system": 0,
            "user": 0,
            "assistant": 0,
            "tool_calls": 0,
            "tool_results": 0,
            "total": 0
        }
        for msg in messages:
            role_key = msg.role if msg.role in result else "user"
            tokens = self.count_fast(msg.content)
            result[role_key] += tokens
            result["total"] += tokens
        return result
```

### 3.2 閾值監控與告警

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Context Window 監控儀表板                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Token 使用量指標:                                                            │
│  ────────────────                                                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Current Usage:  45,230 / 128,000 tokens (35.3%)                    │    │
│  │  ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  35%               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  分段使用量:                                                                  │
│  ───────────                                                                 │
│  System Prompt:     8,200 tokens  ██████                                    │
│  Tools Definition:  3,800 tokens  ████                                      │
│  Conv. History:    28,430 tokens  ██████████████████████                    │
│  Current Input:     4,800 tokens  █████                                     │
│                                                                              │
│  告警閾值:                                                                    │
│  ─────────                                                                   │
│  🟢 綠色區域:  0% - 50%   (正常運作)                                         │
│  🟡 黃色區域: 50% - 75%   (建議壓縮)                                         │
│  🟠 橙色區域: 75% - 90%   (自動壓縮)                                         │
│  🔴 紅色區域: 90% - 100%  (強制壓縮 + 告警)                                  │
│                                                                              │
│  當前狀態: 🟢 正常                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 識別觸發點

```python
# 推薦實現 (新增功能)

class ContextWindowMonitor:
    """Context Window 監控器"""

    def __init__(self, config: ContextConfig):
        self.max_tokens = config.max_context_tokens
        self.thresholds = {
            "green": 0.50,    # 50% - 正常
            "yellow": 0.75,   # 75% - 建議壓縮
            "orange": 0.90,   # 90% - 自動壓縮
            "red": 1.00       # 100% - 強制壓縮
        }
        self.token_counter = TokenCounter()

    def check_status(self, context: SessionContext) -> ContextStatus:
        """檢查當前 context 狀態"""

        # 計算各部分 token 使用量
        usage = {
            "system": self.token_counter.count_fast(context.system_prompt),
            "tools": self.token_counter.count_fast(str(context.tools)),
            "history": self.token_counter.count_messages(context.messages),
            "current": self.token_counter.count_fast(context.current_input),
        }
        total = sum(usage.values())
        ratio = total / self.max_tokens

        # 判斷狀態
        if ratio >= self.thresholds["orange"]:
            return ContextStatus.CRITICAL  # 需要立即壓縮
        elif ratio >= self.thresholds["yellow"]:
            return ContextStatus.WARNING    # 建議壓縮
        else:
            return ContextStatus.NORMAL     # 正常

    def should_compact(self, context: SessionContext) -> Tuple[bool, str]:
        """判斷是否需要壓縮"""
        status = self.check_status(context)

        if status == ContextStatus.CRITICAL:
            return (True, "auto_critical")
        elif status == ContextStatus.WARNING:
            # 檢查是否有長時間運行的對話
            if len(context.messages) > 50:
                return (True, "auto_length")
            # 檢查是否有大量工具調用
            if context.tool_call_count > 20:
                return (True, "auto_tools")
        return (False, "none")
```

---

## 第四部分：控制策略與實現

### 4.1 壓縮策略矩陣

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Context 壓縮策略矩陣                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐                   │
│  │ 壓縮程度     │ 輕度壓縮     │ 中度壓縮     │ 重度壓縮     │                   │
│  ├─────────────┼─────────────┼─────────────┼─────────────┤                   │
│  │ 觸發閾值    │ 50-75%      │ 75-90%      │ 90%+        │                   │
│  │ 目標釋放    │ ~20%        │ ~40%        │ ~60%        │                   │
│  │ 信息損失    │ < 5%        │ 10-20%      │ 20-40%      │                   │
│  │ 執行時間    │ < 100ms     │ < 500ms     │ < 2000ms    │                   │
│  ├─────────────┼─────────────┼─────────────┼─────────────┤                   │
│  │ 對話歷史    │ 保留 20 條   │ 保留 10 條   │ 僅摘要       │                   │
│  │ 工具記錄    │ 保留結果     │ 摘要化       │ 僅統計       │                   │
│  │ 中間狀態    │ 完整保留     │ 選擇性保留   │ 丟棄         │                   │
│  │ System Prompt│ 不變        │ 不變        │ 精簡版       │                   │
│  └─────────────┴─────────────┴─────────────┴─────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 智能壓縮演算法

```python
# 推薦實現 (新增功能)

class IntelligentContextCompressor:
    """智能上下文壓縮器"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client  # 用於生成摘要
        self.importance_scorer = ImportanceScorer()

    async def compress(
        self,
        context: SessionContext,
        target_ratio: float = 0.5,  # 目標壓縮到原大小的 50%
        strategy: CompressStrategy = CompressStrategy.INTELLIGENT
    ) -> CompressedContext:
        """執行壓縮"""

        if strategy == CompressStrategy.SIMPLE_TRUNCATE:
            return self._simple_truncate(context, target_ratio)
        elif strategy == CompressStrategy.SLIDING_WINDOW:
            return self._sliding_window(context, target_ratio)
        elif strategy == CompressStrategy.INTELLIGENT:
            return await self._intelligent_compress(context, target_ratio)
        elif strategy == CompressStrategy.HYBRID:
            return await self._hybrid_compress(context, target_ratio)

    def _simple_truncate(self, context: SessionContext, target_ratio: float) -> CompressedContext:
        """簡單截斷策略 - 保留最近的消息"""
        target_count = int(len(context.messages) * target_ratio)
        return CompressedContext(
            messages=context.messages[-target_count:],
            summary=None,
            dropped_count=len(context.messages) - target_count,
            strategy="simple_truncate"
        )

    def _sliding_window(self, context: SessionContext, target_ratio: float) -> CompressedContext:
        """滑動窗口策略 - 保留窗口內消息"""
        window_size = int(len(context.messages) * target_ratio)
        return CompressedContext(
            messages=context.messages[-window_size:],
            summary=self._quick_summary(context.messages[:-window_size]),
            dropped_count=len(context.messages) - window_size,
            strategy="sliding_window"
        )

    async def _intelligent_compress(self, context: SessionContext, target_ratio: float) -> CompressedContext:
        """智能壓縮策略 - 基於重要性評分"""

        # Step 1: 評估每條消息的重要性
        scored_messages = []
        for msg in context.messages:
            score = self.importance_scorer.score(msg)
            scored_messages.append((msg, score))

        # Step 2: 按重要性排序，保留高重要性消息
        scored_messages.sort(key=lambda x: x[1], reverse=True)
        target_count = int(len(context.messages) * target_ratio)

        # Step 3: 總是保留最近 5 條消息 (時序重要性)
        recent_5 = context.messages[-5:]
        recent_5_set = set(id(m) for m in recent_5)

        # Step 4: 從高分消息中選擇，但排除已選的最近消息
        selected = list(recent_5)
        remaining_quota = target_count - 5

        for msg, score in scored_messages:
            if id(msg) not in recent_5_set and len(selected) < target_count:
                selected.append(msg)

        # Step 5: 對被丟棄的消息生成摘要
        dropped_messages = [m for m in context.messages if m not in selected]
        summary = await self._generate_summary(dropped_messages) if self.llm else None

        # Step 6: 按原始順序排列
        selected.sort(key=lambda m: context.messages.index(m))

        return CompressedContext(
            messages=selected,
            summary=summary,
            dropped_count=len(dropped_messages),
            strategy="intelligent",
            importance_scores={id(m): s for m, s in scored_messages[:len(selected)]}
        )

    async def _hybrid_compress(self, context: SessionContext, target_ratio: float) -> CompressedContext:
        """混合策略 - 結合多種方法"""

        # 對話歷史: 智能壓縮
        history_compressed = await self._intelligent_compress(
            SessionContext(messages=context.messages),
            target_ratio
        )

        # 工具調用記錄: 摘要化
        tool_summary = self._summarize_tool_calls(context.tool_calls)

        # 中間狀態: 選擇性保留
        important_states = {
            k: v for k, v in context.intermediate_states.items()
            if self.importance_scorer.score_state(k, v) > 0.5
        }

        return CompressedContext(
            messages=history_compressed.messages,
            summary=history_compressed.summary,
            tool_summary=tool_summary,
            intermediate_states=important_states,
            dropped_count=history_compressed.dropped_count,
            strategy="hybrid"
        )

    async def _generate_summary(self, messages: List[Message]) -> str:
        """使用 LLM 生成摘要"""
        if not self.llm or not messages:
            return self._quick_summary(messages)

        prompt = f"""請為以下對話歷史生成簡潔摘要，保留關鍵信息：

{self._format_messages(messages)}

摘要（100字以內）："""

        response = await self.llm.complete(prompt, max_tokens=150)
        return response.content

    def _quick_summary(self, messages: List[Message]) -> str:
        """快速摘要（不使用 LLM）"""
        if not messages:
            return ""

        # 提取關鍵詞和主題
        topics = set()
        for msg in messages:
            # 簡單的關鍵詞提取
            words = msg.content.split()[:10]
            topics.update(w for w in words if len(w) > 3)

        return f"[Earlier conversation covering: {', '.join(list(topics)[:5])}...]"


class ImportanceScorer:
    """消息重要性評分器"""

    def score(self, message: Message) -> float:
        """評估單條消息的重要性 (0-1)"""
        score = 0.5  # 基礎分

        # 角色加權
        if message.role == "user":
            score += 0.1  # 用戶消息略重要

        # 長度加權（太短或太長都減分）
        length = len(message.content)
        if 100 < length < 500:
            score += 0.1  # 中等長度最佳
        elif length < 50:
            score -= 0.1  # 太短可能是確認性消息
        elif length > 1000:
            score -= 0.05  # 太長可能是冗餘資訊

        # 關鍵詞加權
        important_keywords = [
            "重要", "關鍵", "必須", "決定", "結論",
            "important", "critical", "must", "decision", "conclusion"
        ]
        if any(kw in message.content.lower() for kw in important_keywords):
            score += 0.15

        # 問題類消息加權
        if "?" in message.content or "？" in message.content:
            score += 0.1

        # 工具調用結果加權
        if message.tool_call_id or "tool_result" in str(message):
            score += 0.1

        return min(1.0, max(0.0, score))

    def score_state(self, key: str, value: Any) -> float:
        """評估中間狀態的重要性"""
        # 特定鍵名的重要性映射
        important_keys = ["decision", "result", "conclusion", "error", "approval"]
        if any(k in key.lower() for k in important_keys):
            return 0.8
        return 0.3
```

### 4.3 手動與自動控制接口

```python
# API 接口設計 (新增功能)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/context", tags=["Context Management"])


class CompactRequest(BaseModel):
    session_id: str
    strategy: Optional[str] = "intelligent"  # simple, sliding_window, intelligent, hybrid
    target_ratio: Optional[float] = 0.5
    preserve_recent: Optional[int] = 10


class ContextStatus(BaseModel):
    session_id: str
    current_tokens: int
    max_tokens: int
    usage_ratio: float
    status: str  # normal, warning, critical
    recommendation: Optional[str]


@router.get("/{session_id}/status", response_model=ContextStatus)
async def get_context_status(session_id: str):
    """獲取 context window 使用狀態"""
    monitor = ContextWindowMonitor()
    session = await session_manager.get(session_id)

    if not session:
        raise HTTPException(404, "Session not found")

    status = monitor.check_status(session.context)
    usage = monitor.get_usage_details(session.context)

    return ContextStatus(
        session_id=session_id,
        current_tokens=usage["total"],
        max_tokens=monitor.max_tokens,
        usage_ratio=usage["total"] / monitor.max_tokens,
        status=status.value,
        recommendation=_get_recommendation(status)
    )


@router.post("/{session_id}/compact")
async def compact_context(session_id: str, request: CompactRequest):
    """手動觸發 context 壓縮"""
    session = await session_manager.get(session_id)

    if not session:
        raise HTTPException(404, "Session not found")

    compressor = IntelligentContextCompressor(llm_client=llm)

    # 執行壓縮
    compressed = await compressor.compress(
        context=session.context,
        target_ratio=request.target_ratio,
        strategy=CompressStrategy[request.strategy.upper()]
    )

    # 更新 session
    session.context.messages = compressed.messages
    session.context.summary = compressed.summary
    await session_manager.save(session)

    # 創建 checkpoint
    await checkpoint_manager.create(
        session_id=session_id,
        checkpoint_type=CheckpointType.MANUAL,
        metadata={"reason": "manual_compact", "dropped": compressed.dropped_count}
    )

    return {
        "success": True,
        "dropped_messages": compressed.dropped_count,
        "new_token_count": monitor.count_tokens(session.context),
        "summary": compressed.summary
    }


@router.post("/{session_id}/auto-compact/enable")
async def enable_auto_compact(session_id: str, threshold: float = 0.75):
    """啟用自動壓縮"""
    await auto_compact_manager.enable(session_id, threshold)
    return {"success": True, "threshold": threshold}


@router.post("/{session_id}/auto-compact/disable")
async def disable_auto_compact(session_id: str):
    """禁用自動壓縮"""
    await auto_compact_manager.disable(session_id)
    return {"success": True}
```

---

## 第五部分：長期對話的實現方案

### 5.1 智能體集群的上下文傳遞架構

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  智能體集群 Context 傳遞架構                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Orchestrator (編排器)                                                 │  │
│  │                                                                        │  │
│  │  Global Context Pool:                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │ • Session Metadata (session_id, user_id, start_time)            │  │  │
│  │  │ • Shared Variables (跨 Agent 共享的變量)                        │  │  │
│  │  │ • Conversation Summary (全局對話摘要)                           │  │  │
│  │  │ • Decision History (決策歷史摘要)                               │  │  │
│  │  │ • Current Goal (當前任務目標)                                   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│         ┌────────────────────┼────────────────────┐                          │
│         │                    │                    │                          │
│         ▼                    ▼                    ▼                          │
│  ┌─────────────┐     ┌─────────────┐      ┌─────────────┐                    │
│  │   Agent A   │     │   Agent B   │      │   Agent C   │                    │
│  │  (診斷專家)  │     │  (修復專家)  │      │  (驗證專家)  │                    │
│  └─────────────┘     └─────────────┘      └─────────────┘                    │
│         │                    │                    │                          │
│         ▼                    ▼                    ▼                          │
│  ┌─────────────┐     ┌─────────────┐      ┌─────────────┐                    │
│  │ Local Context│     │ Local Context│      │ Local Context│                    │
│  │             │     │             │      │             │                    │
│  │ • Agent角色  │     │ • Agent角色  │      │ • Agent角色  │                    │
│  │ • 專業知識   │     │ • 專業知識   │      │ • 專業知識   │                    │
│  │ • 任務歷史   │     │ • 任務歷史   │      │ • 任務歷史   │                    │
│  │ • 工具結果   │     │ • 工具結果   │      │ • 工具結果   │                    │
│  └─────────────┘     └─────────────┘      └─────────────┘                    │
│                                                                              │
│  Context 傳遞規則:                                                            │
│  ──────────────────                                                          │
│  1. Handoff 時: 傳遞 Global + 任務相關 Local (壓縮後)                         │
│  2. 並行執行: 各 Agent 獨立維護 Local, 共享 Global 只讀                       │
│  3. 合併結果: 將各 Agent 結果聚合到 Global                                    │
│  4. 長任務: 定期將重要 Local 晉升到 Global 摘要                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 跨 Agent Handoff 的上下文傳遞

```python
# 推薦實現 (新增功能)

class HandoffContextManager:
    """Handoff 上下文管理器"""

    async def prepare_handoff_context(
        self,
        source_agent: AgentContext,
        target_agent_type: str,
        handoff_reason: str
    ) -> HandoffContext:
        """準備 Handoff 時傳遞的上下文"""

        # 1. 提取關鍵信息
        key_findings = self._extract_key_findings(source_agent.history)

        # 2. 壓縮對話歷史
        compressor = IntelligentContextCompressor()
        compressed = await compressor.compress(
            context=source_agent,
            target_ratio=0.3,  # Handoff 時壓縮到 30%
            strategy=CompressStrategy.INTELLIGENT
        )

        # 3. 構建 Handoff Context
        return HandoffContext(
            # 元數據
            source_agent=source_agent.agent_id,
            target_agent_type=target_agent_type,
            handoff_reason=handoff_reason,
            timestamp=datetime.utcnow(),

            # 壓縮的歷史
            conversation_summary=compressed.summary,
            key_messages=compressed.messages[-5:],  # 最近 5 條

            # 關鍵信息
            key_findings=key_findings,
            attempted_solutions=self._get_attempted_solutions(source_agent),
            error_messages=self._get_error_messages(source_agent),

            # 當前狀態
            current_variables=source_agent.variables,
            pending_tasks=source_agent.pending_tasks,

            # MAF Checkpoint 引用
            checkpoint_id=source_agent.latest_checkpoint_id
        )

    def _extract_key_findings(self, history: List[Message]) -> List[str]:
        """提取關鍵發現"""
        findings = []
        keywords = ["發現", "問題是", "原因是", "found", "issue", "root cause"]

        for msg in history:
            if any(kw in msg.content.lower() for kw in keywords):
                # 提取該消息的核心句子
                sentences = msg.content.split("。")
                for s in sentences:
                    if any(kw in s.lower() for kw in keywords):
                        findings.append(s.strip())
                        break

        return findings[:5]  # 最多 5 個關鍵發現

    def _get_attempted_solutions(self, context: AgentContext) -> List[str]:
        """提取已嘗試的解決方案"""
        solutions = []
        for action in context.action_history:
            if action.type in ["tool_call", "remediation"]:
                solutions.append(f"{action.name}: {action.result_summary}")
        return solutions[-5:]  # 最近 5 個嘗試

    def _get_error_messages(self, context: AgentContext) -> List[str]:
        """提取錯誤信息"""
        errors = []
        for action in context.action_history:
            if action.status == "error":
                errors.append(action.error_message)
        return errors[-3:]  # 最近 3 個錯誤
```

### 5.3 長期對話的 Checkpoint 策略

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  長期對話 Checkpoint 策略                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  時間軸: ─────●─────●─────●─────●─────●─────●─────●─────●──────→             │
│         T0   T1    T2    T3    T4    T5    T6    T7    T8                    │
│                                                                              │
│  Checkpoint 類型與觸發:                                                       │
│  ────────────────────                                                        │
│                                                                              │
│  T0: [START] 會話開始                                                         │
│       └─ 創建初始 Checkpoint (full snapshot)                                 │
│                                                                              │
│  T1-T4: [AUTO] 自動 Checkpoint (每 5 輪對話)                                  │
│       └─ 增量 Checkpoint (delta from previous)                               │
│                                                                              │
│  T5: [HITL] 進入人工審批                                                      │
│       └─ 完整 Checkpoint (等待期間可能有外部變更)                             │
│                                                                              │
│  T6: [MODE_SWITCH] MAF ⇄ Claude 切換                                         │
│       └─ 雙向同步 Checkpoint (確保兩邊一致)                                   │
│                                                                              │
│  T7: [MILESTONE] 重要任務完成                                                 │
│       └─ 帶摘要的 Checkpoint (包含階段性成果)                                 │
│                                                                              │
│  T8: [END] 會話結束                                                           │
│       └─ 最終 Checkpoint + 晉升到長期記憶                                    │
│                                                                              │
│  ────────────────────────────────────────────────────────────────────────── │
│                                                                              │
│  Checkpoint 數據結構:                                                         │
│  ────────────────────                                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Checkpoint {                                                        │    │
│  │    id: "ckpt_abc123"                                                 │    │
│  │    type: "AUTO" | "HITL" | "MODE_SWITCH" | "MILESTONE" | ...        │    │
│  │    timestamp: "2026-01-28T10:30:00Z"                                 │    │
│  │    session_id: "sess_xyz789"                                         │    │
│  │                                                                       │    │
│  │    // MAF 狀態                                                        │    │
│  │    maf_state: {                                                       │    │
│  │      workflow_id: "wf_001"                                            │    │
│  │      current_step: 3                                                  │    │
│  │      agent_states: { ... }                                            │    │
│  │    }                                                                  │    │
│  │                                                                       │    │
│  │    // Claude 狀態                                                     │    │
│  │    claude_state: {                                                    │    │
│  │      context_variables: { ... }                                       │    │
│  │      conversation_summary: "..."                                      │    │
│  │      total_tokens: 45230                                              │    │
│  │    }                                                                  │    │
│  │                                                                       │    │
│  │    // 壓縮的對話歷史 (zlib)                                           │    │
│  │    compressed_history: <bytes>                                        │    │
│  │                                                                       │    │
│  │    // 元數據                                                          │    │
│  │    metadata: {                                                        │    │
│  │      reason: "auto_5_turns"                                           │    │
│  │      token_usage_ratio: 0.35                                          │    │
│  │      message_count: 42                                                │    │
│  │    }                                                                  │    │
│  │  }                                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  存儲策略:                                                                    │
│  ──────────                                                                  │
│  • 最近 5 個 Checkpoint: Redis (快速恢復)                                    │
│  • 7 天內的 Checkpoint: PostgreSQL (持久化)                                  │
│  • 重要 Milestone: Long-term Memory (永久)                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 會話恢復機制

```python
# 推薦實現 (新增功能)

class SessionRecoveryManager:
    """會話恢復管理器"""

    async def recover_session(
        self,
        session_id: str,
        recovery_point: Optional[str] = None  # checkpoint_id
    ) -> RecoveredSession:
        """從 Checkpoint 恢復會話"""

        # 1. 獲取 Checkpoint
        if recovery_point:
            checkpoint = await self.checkpoint_store.get(recovery_point)
        else:
            # 獲取最近的有效 Checkpoint
            checkpoint = await self.checkpoint_store.get_latest(session_id)

        if not checkpoint:
            raise RecoveryError(f"No checkpoint found for session {session_id}")

        # 2. 解壓對話歷史
        history = self._decompress_history(checkpoint.compressed_history)

        # 3. 恢復 MAF 狀態
        maf_context = await self.maf_recovery.restore(checkpoint.maf_state)

        # 4. 恢復 Claude 狀態
        claude_context = ClaudeContext(
            session_id=session_id,
            context_variables=checkpoint.claude_state.context_variables,
            conversation_history=history,
            total_tokens=checkpoint.claude_state.total_tokens
        )

        # 5. 同步兩邊狀態
        await self.context_bridge.sync(maf_context, claude_context)

        # 6. 獲取恢復摘要
        summary = await self._generate_recovery_summary(checkpoint)

        return RecoveredSession(
            session_id=session_id,
            maf_context=maf_context,
            claude_context=claude_context,
            recovery_point=checkpoint.id,
            recovery_summary=summary,
            recovered_at=datetime.utcnow()
        )

    async def _generate_recovery_summary(self, checkpoint: Checkpoint) -> str:
        """生成恢復摘要，提醒用戶上次進度"""

        summary_parts = [
            f"會話已從 {checkpoint.timestamp.strftime('%Y-%m-%d %H:%M')} 的狀態恢復。",
            f"上次對話共 {checkpoint.metadata.get('message_count', '未知')} 條消息。"
        ]

        if checkpoint.claude_state.conversation_summary:
            summary_parts.append(f"上次進度摘要: {checkpoint.claude_state.conversation_summary}")

        if checkpoint.maf_state:
            summary_parts.append(f"工作流步驟: {checkpoint.maf_state.current_step}")

        return "\n".join(summary_parts)

    def _decompress_history(self, compressed: bytes) -> List[Message]:
        """解壓對話歷史"""
        import zlib
        import json

        decompressed = zlib.decompress(compressed).decode("utf-8")
        history_data = json.loads(decompressed)

        return [Message(**msg) for msg in history_data]
```

---

## 第六部分：實施建議與路線圖

### 6.1 與現有架構的整合點

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Context Window 管理與現有架構整合                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  現有組件                        新增/強化組件                               │
│  ────────                        ────────────                               │
│                                                                              │
│  SessionStateManager    ──────▶  TokenCounter (精確計數)                     │
│  (claude_sdk/session_state.py)   ContextWindowMonitor (閾值監控)            │
│                                                                              │
│  UnifiedMemoryManager   ──────▶  IntelligentContextCompressor               │
│  (memory/unified_memory.py)      (智能壓縮演算法)                            │
│                                                                              │
│  ContextBridge          ──────▶  HandoffContextManager                       │
│  (hybrid/context/bridge.py)      (跨 Agent 上下文優化)                       │
│                                                                              │
│  HybridCheckpointManager ─────▶  SessionRecoveryManager                      │
│  (hybrid/checkpoint/)            (會話恢復增強)                              │
│                                                                              │
│  API Routes             ──────▶  /api/v1/context/                           │
│  (api/v1/)                       (Context 管理 API)                          │
│                                                                              │
│  Frontend (unified-chat) ─────▶  ContextStatusIndicator                     │
│  (components/unified-chat/)      (Token 使用量顯示)                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 實施路線圖

```
Phase 1: 基礎監控 (Week 1-2)
══════════════════════════════

目標: 實現 Context Window 使用量的精確追蹤與告警

任務:
├── [ ] 實現 TokenCounter 類 (支援多模型)
├── [ ] 實現 ContextWindowMonitor 類
├── [ ] 新增 /api/v1/context/{session_id}/status API
├── [ ] 前端新增 Token 使用量指示器
└── [ ] 整合到現有 OrchestrationMetrics

交付物:
• 實時 Token 使用量追蹤
• 閾值告警機制 (50%, 75%, 90%)
• Grafana/Dashboard 指標面板


Phase 2: 智能壓縮 (Week 3-4)
══════════════════════════════

目標: 實現多策略智能壓縮系統

任務:
├── [ ] 實現 IntelligentContextCompressor 類
├── [ ] 實現 ImportanceScorer 重要性評分
├── [ ] 整合 LLM 摘要生成 (可選)
├── [ ] 新增 /api/v1/context/{session_id}/compact API
├── [ ] 實現自動壓縮觸發機制
└── [ ] 前端新增手動壓縮按鈕

交付物:
• 4 種壓縮策略 (simple, sliding, intelligent, hybrid)
• 自動/手動壓縮接口
• 壓縮效果統計


Phase 3: Checkpoint 強化 (Week 5-6)
════════════════════════════════════

目標: 強化 MAF Checkpoint 與 Context 的整合

任務:
├── [ ] 擴展 HybridCheckpoint 數據結構
├── [ ] 實現增量 Checkpoint (delta)
├── [ ] 實現 SessionRecoveryManager
├── [ ] 新增 /api/v1/checkpoint/recover API
├── [ ] 整合到 Handoff 流程
└── [ ] 實現 Checkpoint 清理策略

交付物:
• 增量 Checkpoint 機制
• 會話恢復功能
• Checkpoint 生命週期管理


Phase 4: 智能體集群優化 (Week 7-8)
════════════════════════════════════

目標: 優化多 Agent 場景的 Context 傳遞

任務:
├── [ ] 實現 HandoffContextManager
├── [ ] 優化 GroupChat 上下文管理
├── [ ] 實現 Global/Local Context 分離
├── [ ] 優化並行 Agent 的上下文隔離
└── [ ] 性能測試與優化

交付物:
• Handoff 上下文壓縮傳遞
• 多 Agent 上下文隔離
• 性能基準測試報告
```

### 6.3 預估工作量

| 階段 | 任務數 | 預估工時 | 依賴 |
|------|--------|---------|------|
| Phase 1: 基礎監控 | 6 | 5 人天 | 無 |
| Phase 2: 智能壓縮 | 7 | 8 人天 | Phase 1 |
| Phase 3: Checkpoint 強化 | 7 | 8 人天 | Phase 1 |
| Phase 4: 集群優化 | 6 | 6 人天 | Phase 2, 3 |
| **總計** | **26** | **27 人天** | |

### 6.4 風險與緩解

| 風險 | 影響 | 可能性 | 緩解措施 |
|------|------|--------|---------|
| LLM 摘要質量不穩定 | 壓縮後信息損失 | 中 | 保留原始備份、可選關閉 LLM 摘要 |
| Token 計數不精確 | 閾值判斷偏差 | 低 | 使用保守閾值、定期校準 |
| Checkpoint 數據過大 | 存儲成本增加 | 中 | 實現增量存儲、清理策略 |
| 恢復時狀態不一致 | 對話中斷 | 低 | 完整性校驗、回滾機制 |
| 多 Agent 同步延遲 | 上下文過時 | 中 | 版本控制、衝突解決 |

---

## 第七部分：總結與建議

### 7.1 核心架構決策

1. **分層記憶架構**
   - 保持現有三層記憶系統 (Working/Session/Long-term)
   - 強化層間晉升機制，增加使用頻率和衰減因子

2. **智能壓縮策略**
   - 採用 Hybrid 策略作為默認
   - 基於重要性評分保留關鍵信息
   - 可選 LLM 摘要提升壓縮質量

3. **MAF Checkpoint 整合**
   - Checkpoint 作為「恢復點」和「記憶錨點」
   - 增量存儲減少空間消耗
   - 與 Context 壓縮協同工作

4. **智能體集群設計**
   - Global/Local Context 分離
   - Handoff 時傳遞壓縮後的上下文
   - 並行 Agent 獨立維護 Local，共享 Global

### 7.2 與業界工具對比

| 特性 | Claude Code | IPA Platform (目標) |
|------|-------------|---------------------|
| 自動壓縮 | ✅ Auto-compact | ✅ 閾值觸發 + 自動壓縮 |
| 手動壓縮 | ✅ /compact 命令 | ✅ API + UI 按鈕 |
| 摘要生成 | ✅ 自動摘要 | ✅ 可選 LLM 摘要 |
| 持久化 | ❌ 會話內 | ✅ 三層記憶 + Checkpoint |
| 會話恢復 | ⚠️ 有限 | ✅ 完整恢復機制 |
| 多 Agent | ❌ 單 Agent | ✅ 集群上下文管理 |
| 可觀測性 | ⚠️ 有限 | ✅ 完整指標追蹤 |

### 7.3 關鍵收益

1. **用戶體驗**
   - 長時間對話不中斷
   - 上下文限制透明可見
   - 一鍵恢復歷史會話

2. **系統效能**
   - 減少不必要的 Token 消耗
   - 優化 LLM API 成本
   - 提升響應速度

3. **企業治理**
   - 完整的對話審計追蹤
   - 可解釋的壓縮決策
   - 符合合規要求的數據持久化

### 7.4 下一步行動

1. **立即**: 實現 TokenCounter 和 ContextWindowMonitor 基礎監控
2. **短期**: 完成智能壓縮系統，整合到現有 SessionStateManager
3. **中期**: 強化 Checkpoint 機制，實現會話恢復
4. **長期**: 優化多 Agent 場景，建立完整的上下文生命週期管理

---

## 附錄 A: 代碼位置參考

| 組件 | 現有位置 | 建議新增位置 |
|------|----------|-------------|
| Token 計數 | (無) | `integrations/context/token_counter.py` |
| 監控器 | (無) | `integrations/context/monitor.py` |
| 壓縮器 | session_state.py (部分) | `integrations/context/compressor.py` |
| 重要性評分 | (無) | `integrations/context/importance_scorer.py` |
| 會話恢復 | (無) | `integrations/context/recovery.py` |
| Handoff 管理 | handoff_context.py (部分) | `integrations/context/handoff_manager.py` |
| API 路由 | (無) | `api/v1/context/routes.py` |
| 前端組件 | (無) | `components/unified-chat/ContextStatusIndicator.tsx` |

## 附錄 B: 配置參數參考

```python
# context_config.py

class ContextWindowConfig:
    """Context Window 管理配置"""

    # Token 限制
    max_context_tokens: int = 100000        # 最大 Token 數 (留 28K 給輸出)
    reserved_for_output: int = 28000        # 輸出保留空間

    # 閾值設定
    warning_threshold: float = 0.50         # 50% - 黃色告警
    auto_compact_threshold: float = 0.75    # 75% - 自動壓縮
    critical_threshold: float = 0.90        # 90% - 強制壓縮

    # 壓縮參數
    default_compress_strategy: str = "hybrid"
    preserve_recent_messages: int = 10      # 保留最近 N 條
    target_compress_ratio: float = 0.5      # 目標壓縮比

    # Checkpoint 參數
    auto_checkpoint_interval: int = 5       # 每 N 輪自動 Checkpoint
    max_checkpoint_history: int = 10        # 保留最近 N 個 Checkpoint
    checkpoint_ttl_days: int = 7            # Checkpoint 保留天數

    # 智能體集群參數
    handoff_context_ratio: float = 0.3      # Handoff 時壓縮到 30%
    global_context_max_size: int = 5000     # Global Context 最大 Token
    local_context_max_size: int = 20000     # Local Context 最大 Token
```

---

**文件結束**

*Generated by Claude Code Analysis - 2026-01-28*
