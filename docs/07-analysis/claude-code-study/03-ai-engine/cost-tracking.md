# Cost and Usage Tracking — Claude Code CLI

> Source: `src/cost-tracker.ts`, `src/utils/modelCost.ts`, `src/services/api/usage.ts`, `src/services/policyLimits/`

## Overview

Cost tracking aggregates token usage and USD costs across a session, displays running totals, and enforces policy-based limits.

## Pricing Tables (`src/utils/modelCost.ts`)

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| claude-opus-4-6 (standard) | $5 | $25 | $6.25 | $0.50 |
| claude-opus-4-6 (fast mode) | $30 | $150 | $37.50 | $3.00 |
| claude-sonnet-4-6/4-5/4-0 | $3 | $15 | $3.75 | $0.30 |
| claude-haiku-4-5 | $1 | $5 | $1.25 | $0.10 |

Fast mode tier selected by `usage.speed === 'fast'` in API response.

## Cost Calculation

```
cost = (input_tokens / 1M) * inputPrice
     + (output_tokens / 1M) * outputPrice
     + (cache_read / 1M) * cacheReadPrice
     + (cache_creation / 1M) * cacheWritePrice
     + web_search_requests * $0.01
```

Unknown models fall back to default pricing and log `tengu_unknown_model_cost`.

## Session Aggregation (`src/cost-tracker.ts`, `src/bootstrap/state.ts`)

Cumulative counters: `totalCostUSD`, `totalInputTokens`, `totalOutputTokens`, `totalCacheReadInputTokens`, `totalCacheCreationInputTokens`, `totalWebSearchRequests`, `totalAPIDuration`, `totalToolDuration`, `totalLinesAdded/Removed`, `modelUsage` (per-model breakdown).

## Cost Hook (`src/costHook.ts`)

After each API response:
1. `calculateUSDCost(model, usage)` → resolve canonical name → lookup pricing → calculate
2. `addToTotalSessionCost()` → increment all counters
3. `logEvent('tengu_api_usage', {...})` → analytics

## Rate Limits (`src/services/api/usage.ts`)

For Claude.ai subscribers, `fetchUtilization()` queries `/api/oauth/usage`:
```typescript
{ five_hour?, seven_day?, seven_day_opus?, seven_day_sonnet?, extra_usage? }
```

## Policy Limits (`src/services/policyLimits/`)

Enterprise organizations configure restrictions via Anthropic API.

- **Eligibility**: Console users and Team/Enterprise OAuth
- **Loading**: `loadPolicyLimits()` with retry, cached in `~/.claude/policy-limits.json`
- **Polling**: Every 1 hour for updates
- **Fail-open**: Unreachable endpoint → all policies allowed
- **Check**: `isPolicyAllowed(policy)` — synchronous at feature boundaries

## Key Design Decisions

1. **Fail-open policy limits**: Service availability > restriction enforcement
2. **Background polling**: Policy changes effective within 1 hour without restart
3. **Fast mode pricing split**: API reports `speed === 'fast'` explicitly for correct costing
4. **Per-model breakdown**: `modelUsage` map shows exact cost per model in mixed sessions
