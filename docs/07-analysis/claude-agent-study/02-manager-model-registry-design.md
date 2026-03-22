# ManagerModelRegistry + ManagerModelSelector 設計方案

## 日期：2026-03-22
## 背景：用戶提出的多模型動態選擇架構

---

## 設計概念

### ManagerModelRegistry — 靜態配置層（定義「有什麼可用」）

```yaml
models:
  claude-opus-4-6:
    provider: anthropic
    model_id: claude-opus-4-6
    capabilities: [adaptive_thinking, tool_use, vision]
    cost_tier: premium
    max_tokens: 200000

  claude-sonnet-4-6:
    provider: anthropic
    model_id: claude-sonnet-4-6
    capabilities: [tool_use, fast]
    cost_tier: standard

  claude-haiku-4-5:
    provider: anthropic
    model_id: claude-haiku-4-5
    capabilities: [tool_use, fast]
    cost_tier: economy

  gpt-5.2:
    provider: azure_openai
    model_id: gpt-5.2
    capabilities: [function_calling, structured_output]
    cost_tier: standard
```

### ManagerModelSelector — 動態決策層（決定「這次用什麼」）

```yaml
routing_rules:
  - intent: incident
    risk: critical
    orchestration: magentic
    manager_model: claude-opus-4-6      # 最強推理
    worker_models: [claude-sonnet-4-6]

  - intent: change
    risk: high
    orchestration: magentic
    manager_model: claude-sonnet-4-6    # 平衡成本
    worker_models: [gpt-5.2]

  - intent: incident
    risk: medium
    orchestration: sequential
    manager_model: gpt-5.2              # 較便宜

  - intent: request
    risk: low
    orchestration: simple
    manager_model: claude-haiku-4-5     # 最快最便宜
```

### 與現有 11 層架構的整合點

```
[L4] BusinessIntentRouter → 意圖分類 → INCIDENT/CHANGE/REQUEST
[L4] RiskAssessor → 風險等級 → LOW/MEDIUM/HIGH/CRITICAL
                ↓
[L5] FrameworkSelector + ManagerModelSelector  ← 新增
  intent=INCIDENT + risk=CRITICAL → Magentic + claude-opus-4-6
  intent=CHANGE + risk=HIGH → Magentic + claude-sonnet-4-6
  intent=INCIDENT + risk=MEDIUM → Sequential + gpt-5.2
  intent=REQUEST + risk=LOW → Simple + claude-haiku-4-5
                ↓
[L6] MagenticBuilderAdapter
  manager_agent = registry.create_manager_agent(selected_model_id)
      ├── Claude Workers
      ├── Azure OpenAI Workers
      └── MCP Tools
```

## 解決的問題

| 問題 | 解法 |
|------|------|
| LLM 綁死在 AzureOpenAILLMService | Registry 統一管理多個 provider |
| 所有請求用同一個模型 | Selector 按 intent + risk 動態選擇 |
| 換模型要改代碼 | YAML 配置零代碼切換 |
| Manager 和 Worker 用同一個模型 | 可以分別配置 |
| 成本不可控 | cost_tier 分層 + token budget |
