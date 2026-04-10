# Model Selection and Routing — Claude Code CLI

> Consolidated from base analysis + deep verification (2026-04-01).
> Source: `src/utils/model/` (16 files, ~2,525 lines of TypeScript)

---

## 1. File Inventory (16 files)

| # | File | Lines | Purpose |
|---|------|-------|---------|
| 1 | `model.ts` | 619 | Central model resolution engine — aliases, defaults, canonical names, display names, runtime selection |
| 2 | `configs.ts` | 119 | `ALL_MODEL_CONFIGS` registry — 11 model configs with per-provider IDs |
| 3 | `aliases.ts` | 26 | `MODEL_ALIASES` constant + `MODEL_FAMILY_ALIASES` + type guards |
| 4 | `modelOptions.ts` | 541 | Model picker UI options — tier-aware option lists for `/model` command |
| 5 | `modelAllowlist.ts` | 171 | Organization-level model restriction — 3-tier matching (family/version-prefix/exact) |
| 6 | `modelCapabilities.ts` | 119 | Remote model capabilities cache — fetches `max_input_tokens`/`max_tokens` from API |
| 7 | `modelStrings.ts` | 167 | Provider-specific model ID resolution — Bedrock inference profiles, model overrides |
| 8 | `agent.ts` | 158 | Subagent model resolution — inherit, alias matching, Bedrock region prefix inheritance |
| 9 | `antModels.ts` | 65 | Anthropic-internal (ant) model config — feature-flag-driven model override system |
| 10 | `bedrock.ts` | 266 | AWS Bedrock integration — client creation, inference profiles, region prefix handling |
| 11 | `check1mAccess.ts` | 73 | 1M context window access checks — extra usage / subscription gating |
| 12 | `contextWindowUpgradeCheck.ts` | 48 | Context window upgrade suggestions — "Tip: You have access to X with 5x more context" |
| 13 | `deprecation.ts` | 102 | Model deprecation warnings — retirement dates per provider |
| 14 | `modelSupportOverrides.ts` | 51 | 3P model capability overrides — effort, thinking, adaptive_thinking via env vars |
| 15 | `providers.ts` | 41 | API provider detection — `firstParty` / `bedrock` / `vertex` / `foundry` |
| 16 | `validateModel.ts` | 160 | Model validation via API probe — side-query with `max_tokens:1`, fallback suggestions |

---

## 2. ALL_MODEL_CONFIGS Registry (`configs.ts`)

The central model configuration registry maps 11 model keys to provider-specific IDs across 4 providers.

### 2.1 Complete Registry

| Key | First-Party ID | Bedrock ID | Vertex ID | Foundry ID |
|-----|----------------|------------|-----------|------------|
| `haiku35` | `claude-3-5-haiku-20241022` | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | `claude-3-5-haiku@20241022` | `claude-3-5-haiku` |
| `haiku45` | `claude-haiku-4-5-20251001` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | `claude-haiku-4-5@20251001` | `claude-haiku-4-5` |
| `sonnet35` | `claude-3-5-sonnet-20241022` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | `claude-3-5-sonnet-v2@20241022` | `claude-3-5-sonnet` |
| `sonnet37` | `claude-3-7-sonnet-20250219` | `us.anthropic.claude-3-7-sonnet-20250219-v1:0` | `claude-3-7-sonnet@20250219` | `claude-3-7-sonnet` |
| `sonnet40` | `claude-sonnet-4-20250514` | `us.anthropic.claude-sonnet-4-20250514-v1:0` | `claude-sonnet-4@20250514` | `claude-sonnet-4` |
| `sonnet45` | `claude-sonnet-4-5-20250929` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | `claude-sonnet-4-5@20250929` | `claude-sonnet-4-5` |
| `sonnet46` | `claude-sonnet-4-6` | `us.anthropic.claude-sonnet-4-6` | `claude-sonnet-4-6` | `claude-sonnet-4-6` |
| `opus40` | `claude-opus-4-20250514` | `us.anthropic.claude-opus-4-20250514-v1:0` | `claude-opus-4@20250514` | `claude-opus-4` |
| `opus41` | `claude-opus-4-1-20250805` | `us.anthropic.claude-opus-4-1-20250805-v1:0` | `claude-opus-4-1@20250805` | `claude-opus-4-1` |
| `opus45` | `claude-opus-4-5-20251101` | `us.anthropic.claude-opus-4-5-20251101-v1:0` | `claude-opus-4-5@20251101` | `claude-opus-4-5` |
| `opus46` | `claude-opus-4-6` | `us.anthropic.claude-opus-4-6-v1` | `claude-opus-4-6` | `claude-opus-4-6` |

### 2.2 Derived Types

```typescript
type ModelKey = 'haiku35' | 'haiku45' | 'sonnet35' | 'sonnet37' | 'sonnet40' | 'sonnet45' | 'sonnet46' | 'opus40' | 'opus41' | 'opus45' | 'opus46'
type CanonicalModelId = (typeof ALL_MODEL_CONFIGS)[ModelKey]['firstParty']  // union of 11 firstParty IDs
const CANONICAL_MODEL_IDS: CanonicalModelId[]  // runtime array for tests
const CANONICAL_ID_TO_KEY: Record<CanonicalModelId, ModelKey>  // reverse lookup
```

---

## 3. Alias Resolution Chain (`aliases.ts` + `model.ts`)

### 3.1 MODEL_ALIASES

```typescript
const MODEL_ALIASES = ['sonnet', 'opus', 'haiku', 'best', 'sonnet[1m]', 'opus[1m]', 'opusplan'] as const
```

### 3.2 MODEL_FAMILY_ALIASES

```typescript
const MODEL_FAMILY_ALIASES = ['sonnet', 'opus', 'haiku'] as const
```

Family aliases act as wildcards in the `availableModels` allowlist — "opus" permits any Opus version.

### 3.3 Resolution via `parseUserSpecifiedModel()`

| Input Alias | Resolution (1P) | Resolution (3P) | Notes |
|-------------|-----------------|------------------|-------|
| `sonnet` | `claude-sonnet-4-6` | `claude-sonnet-4-5-20250929` | 3P defaults to older Sonnet |
| `opus` | `claude-opus-4-6` | `claude-opus-4-6` | Same across providers |
| `haiku` | `claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` | Same across providers |
| `best` | `claude-opus-4-6` | `claude-opus-4-6` | Always maps to `getDefaultOpusModel()` |
| `opusplan` | Sonnet 4.6 (default) / Opus 4.6 (plan mode) | Same pattern | Mode-sensitive dual model |
| `sonnet[1m]` | `claude-sonnet-4-6[1m]` | `claude-sonnet-4-5-20250929[1m]` | 1M suffix appended after alias resolution |
| `opus[1m]` | `claude-opus-4-6[1m]` | `claude-opus-4-6[1m]` | 1M suffix appended after alias resolution |

### 3.4 Full Resolution Pipeline

```
User input string
    |
    v
parseUserSpecifiedModel(input)
    +-- Strip & normalize to lowercase
    +-- Detect [1m] suffix -> set has1mTag flag
    +-- Check isModelAlias() -> switch on alias name -> resolve to provider default
    +-- Check isLegacyOpusFirstParty() -> remap Opus 4.0/4.1 -> current Opus default
    +-- Check USER_TYPE=ant -> resolveAntModel() from feature flag config
    +-- Passthrough: preserve original case for custom model names (e.g. Azure Foundry deployment IDs)
        +-- Re-attach [1m] suffix if detected
```

---

## 4. Provider-Specific ID Mapping (`providers.ts` + `modelStrings.ts`)

### 4.1 Provider Detection

```typescript
type APIProvider = 'firstParty' | 'bedrock' | 'vertex' | 'foundry'

// Detection order (first truthy wins):
CLAUDE_CODE_USE_BEDROCK=1  -> 'bedrock'
CLAUDE_CODE_USE_VERTEX=1   -> 'vertex'
CLAUDE_CODE_USE_FOUNDRY=1  -> 'foundry'
(none)                     -> 'firstParty'
```

### 4.2 ModelStrings Resolution

`getModelStrings()` returns a `Record<ModelKey, string>` with provider-appropriate model IDs.

**Resolution path:**
1. Check `getModelStringsState()` (cached in bootstrap state)
2. If null -> `initModelStrings()`:
   - Non-Bedrock: `getBuiltinModelStrings(provider)` — static lookup from `ALL_MODEL_CONFIGS[key][provider]`
   - Bedrock: background async fetch of inference profiles via `getBedrockInferenceProfiles()`, match by canonical substring
3. Apply `modelOverrides` from `settings.json` (keyed by canonical first-party ID -> arbitrary provider-specific string)

### 4.3 Bedrock Inference Profile Matching

```
For each ModelKey:
  needle = ALL_MODEL_CONFIGS[key].firstParty   (e.g. "claude-opus-4-6")
  match  = profiles.find(p => p.includes(needle))  (e.g. "eu.anthropic.claude-opus-4-6-v1")
  fallback = ALL_MODEL_CONFIGS[key].bedrock     (e.g. "us.anthropic.claude-opus-4-6-v1")
```

### 4.4 Model Override Resolution (`resolveOverriddenModel()`)

Reverse lookup: if input matches an override value (e.g. a Bedrock ARN), returns the canonical first-party ID. Used by `getCanonicalName()` and allowlist checks to normalize custom model IDs.

---

## 5. Canonical Name Resolution (`model.ts`)

### 5.1 `firstPartyNameToCanonical(name)`

Pure string-match that strips date/provider suffixes. Order-dependent checks from most specific to least:

| Pattern Match | Canonical Output |
|---------------|-----------------|
| `claude-opus-4-6` | `claude-opus-4-6` |
| `claude-opus-4-5` | `claude-opus-4-5` |
| `claude-opus-4-1` | `claude-opus-4-1` |
| `claude-opus-4` | `claude-opus-4` |
| `claude-sonnet-4-6` | `claude-sonnet-4-6` |
| `claude-sonnet-4-5` | `claude-sonnet-4-5` |
| `claude-sonnet-4` | `claude-sonnet-4` |
| `claude-haiku-4-5` | `claude-haiku-4-5` |
| `claude-3-7-sonnet` | `claude-3-7-sonnet` |
| `claude-3-5-sonnet` | `claude-3-5-sonnet` |
| `claude-3-5-haiku` | `claude-3-5-haiku` |
| `claude-3-opus` | `claude-3-opus` |
| `claude-3-sonnet` | `claude-3-sonnet` |
| `claude-3-haiku` | `claude-3-haiku` |
| Regex fallback | `/(claude-(\d+-\d+-)?\w+)/` |

### 5.2 `getCanonicalName(fullModelName)`

Pipeline: `resolveOverriddenModel(input)` -> `firstPartyNameToCanonical(resolved)`

Unifies 1P and 3P model IDs to a single canonical form. For example:
- `claude-3-5-haiku-20241022` -> `claude-3-5-haiku`
- `us.anthropic.claude-3-5-haiku-20241022-v1:0` -> `claude-3-5-haiku`

---

## 6. Display Names (`model.ts`)

### 6.1 `getPublicModelDisplayName(model)` — UI Display Names

| Model String | Display Name |
|-------------|-------------|
| `{opus46}` | Opus 4.6 |
| `{opus46}[1m]` | Opus 4.6 (1M context) |
| `{opus45}` | Opus 4.5 |
| `{opus41}` | Opus 4.1 |
| `{opus40}` | Opus 4 |
| `{sonnet46}` | Sonnet 4.6 |
| `{sonnet46}[1m]` | Sonnet 4.6 (1M context) |
| `{sonnet45}` | Sonnet 4.5 |
| `{sonnet45}[1m]` | Sonnet 4.5 (1M context) |
| `{sonnet40}` | Sonnet 4 |
| `{sonnet40}[1m]` | Sonnet 4 (1M context) |
| `{sonnet37}` | Sonnet 3.7 |
| `{sonnet35}` | Sonnet 3.5 |
| `{haiku45}` | Haiku 4.5 |
| `{haiku35}` | Haiku 3.5 |

### 6.2 `getMarketingNameForModel(modelId)` — Marketing Names

Same models but with `(with 1M context)` phrasing for 1M variants. Returns `undefined` for Foundry (deployment IDs are user-defined). Also includes `Claude 3.7 Sonnet` and `Claude 3.5 Sonnet/Haiku` with the `Claude` prefix for legacy 3.x models.

### 6.3 `getPublicModelName(model)` — Git Commit Author Names

Returns `"Claude {DisplayName}"` for public models (e.g. `"Claude Opus 4.6 (1M context)"`), or `"Claude ({model})"` for unrecognized/internal models.

### 6.4 `renderModelName(model)` — Codename Masking for Ants

For ant users with internal codename models, masks the first segment: e.g. `capybara-v2-fast` -> `cap*****-v2-fast`.

---

## 7. Model Capabilities (`modelCapabilities.ts`)

### 7.1 Schema

```typescript
type ModelCapability = {
  id: string
  max_input_tokens?: number
  max_tokens?: number
}
```

### 7.2 Cache System

- **Eligibility**: Only for `USER_TYPE=ant` + `firstParty` provider + first-party base URL
- **Storage**: `~/.claude/cache/model-capabilities.json` with timestamp
- **Fetch**: `anthropic.models.list()` API endpoint, paginated
- **Matching**: Exact ID match first, then substring match (longest-id-first sorting for specificity)
- **Refresh**: `refreshModelCapabilities()` called during bootstrap, writes only if data changed

---

## 8. Model Allowlist (`modelAllowlist.ts`)

### 8.1 Three-Tier Matching

Organizations restrict models via `settings.availableModels` array.

| Tier | Example Entry | Match Behavior |
|------|--------------|----------------|
| **Family alias** | `"opus"` | Wildcard — any Opus model allowed. BUT if more specific entries exist (e.g. `"opus-4-5"`), the wildcard is suppressed |
| **Version prefix** | `"opus-4-5"` or `"claude-opus-4-5"` | Segment-boundary prefix match — `claude-opus-4-5-20251101` matches, `claude-opus-4-50` does not |
| **Full model ID** | `"claude-opus-4-5-20251101"` | Exact match only |

### 8.2 Resolution Logic (ordered)

1. Direct match (alias-to-alias or full-name-to-full-name) — skip if family alias is narrowed
2. Family alias wildcard — only if no specific entries exist for that family
3. Bidirectional alias resolution (resolve input alias -> check list; resolve list aliases -> check input)
4. Version-prefix segment-boundary matching with `claude-` prefix normalization

### 8.3 Key Behaviors

- Empty `availableModels: []` blocks ALL user-specified models
- `availableModels` absent -> no restrictions (all allowed)
- `isModelAllowed()` called by `getUserSpecifiedModelSetting()` — rejected models fall through to tier default

---

## 9. Model Defaults by User Tier (`model.ts`)

### 9.1 `getDefaultMainLoopModelSetting()`

| User Type | Default Setting | Resolved Model |
|-----------|----------------|----------------|
| `ant` (Anthropic employee) | Feature-flag `defaultModel`, or Opus 4.6 [1m] | Varies per flag config |
| Max subscriber | Opus 4.6 + `[1m]` if merge enabled | `claude-opus-4-6[1m]` |
| Team Premium | Opus 4.6 + `[1m]` if merge enabled | `claude-opus-4-6[1m]` |
| Pro / Team Standard / Enterprise | Sonnet (provider default) | `claude-sonnet-4-6` (1P) / `claude-sonnet-4-5-20250929` (3P) |
| PAYG (1P and 3P) | Sonnet (provider default) | Same as above |

### 9.2 Opus 1M Merge (`isOpus1mMergeEnabled()`)

When enabled, Opus and Opus[1m] are merged into a single option in the model picker. Disabled when:
- `is1mContextDisabled()` is true
- User is a Pro subscriber
- Provider is not firstParty
- Claude AI subscriber with unknown `subscriptionType` (stale OAuth token guard)

### 9.3 `getDefaultOpusModel()` / `getDefaultSonnetModel()` / `getDefaultHaikuModel()`

Each has an env var override (`ANTHROPIC_DEFAULT_OPUS_MODEL`, etc.) and a 3P vs 1P branch:

| Function | 1P Default | 3P Default |
|----------|-----------|-----------|
| `getDefaultOpusModel()` | `opus46` | `opus46` |
| `getDefaultSonnetModel()` | `sonnet46` | `sonnet45` |
| `getDefaultHaikuModel()` | `haiku45` | `haiku45` |

---

## 10. Runtime Model Selection (`model.ts`)

### 10.1 `getMainLoopModel()` — Session Model

```
getUserSpecifiedModelSetting()  ->  (has value?)  ->  parseUserSpecifiedModel(value)
                                       | null/undefined
                              getDefaultMainLoopModel()
```

### 10.2 `getRuntimeMainLoopModel()` — Per-Turn Model

Applies permission-mode-based overrides:

| Condition | Resolved Model |
|-----------|---------------|
| User set `opusplan` + currently in `plan` mode + under 200K tokens | Opus (default) |
| User set `haiku` + currently in `plan` mode | Sonnet (default) — upgraded for plan mode |
| Otherwise | `mainLoopModel` passthrough |

### 10.3 `resolveSkillModelOverride(skillModel, currentModel)`

When a skill specifies `model: opus` and the user is on `opus[1m]`, carries the `[1m]` suffix to prevent autocompact at 23% apparent usage. Only carries if target family supports 1M (Sonnet/Opus). Haiku has no 1M variant.

---

## 11. Subagent Model Resolution (`agent.ts`)

### 11.1 Resolution Priority

```
1. CLAUDE_CODE_SUBAGENT_MODEL env var (absolute override)
2. Tool-specified model (from tool frontmatter)
3. Agent config model (from agent definition)
4. Default: 'inherit' (same as parent)
```

### 11.2 Alias-to-Parent Matching (`aliasMatchesParentTier()`)

When subagent specifies a bare family alias that matches the parent's canonical family, the parent's exact model string is inherited. Prevents downgrades (e.g. Vertex user on Opus 4.6 spawning `model: opus` subagent getting an older default).

### 11.3 Bedrock Region Prefix Inheritance

When parent model uses cross-region inference prefix (e.g. `eu.anthropic.claude-...`), subagents inherit the same prefix. Exception: if the agent config explicitly specifies a full model ID with its own region prefix, it is preserved to avoid silent data-residency violations.

### 11.4 Agent Model Options

```typescript
const AGENT_MODEL_OPTIONS = ['sonnet', 'opus', 'haiku', 'best', 'sonnet[1m]', 'opus[1m]', 'opusplan', 'inherit']
```

---

## 12. Bedrock Integration (`bedrock.ts`)

### 12.1 Client Creation

Two clients: `BedrockClient` (for listing profiles) and `BedrockRuntimeClient` (for inference).

- Region: `AWS_REGION` or `AWS_DEFAULT_REGION` env -> fallback `us-east-1`
- Auth: AWS credentials via `refreshAndGetAwsCredentials()`, or skip with `CLAUDE_CODE_SKIP_BEDROCK_AUTH`
- Proxy: `getAWSClientProxyConfig()`
- Custom endpoint: `ANTHROPIC_BEDROCK_BASE_URL`

### 12.2 Inference Profiles

`getBedrockInferenceProfiles()` (memoized) lists `SYSTEM_DEFINED` profiles, filters for Anthropic models.

### 12.3 Region Prefix System

```typescript
const BEDROCK_REGION_PREFIXES = ['us', 'eu', 'apac', 'global'] as const
```

Functions:
- `getBedrockRegionPrefix(modelId)` — extracts prefix from `eu.anthropic.claude-...` or ARN format
- `applyBedrockRegionPrefix(modelId, prefix)` — replaces or adds prefix
- `extractModelIdFromArn(modelId)` — extracts profile ID from ARN format
- `isFoundationModel(modelId)` — checks `anthropic.` prefix
- `getInferenceProfileBackingModel(profileId)` — gets the actual model behind a profile for cost calculation

---

## 13. 1M Context Window Access (`check1mAccess.ts`)

### 13.1 `checkOpus1mAccess()` / `checkSonnet1mAccess()`

Both follow the same logic:
- If `is1mContextDisabled()` -> false
- If Claude AI subscriber -> requires `isExtraUsageEnabled()` (extra usage provisioned)
- Non-subscribers (API/PAYG) -> always true

### 13.2 Extra Usage Disabled Reasons

```typescript
type OverageDisabledReason =
  | 'out_of_credits'              // still counts as enabled (provisioned)
  | 'overage_not_provisioned'     // NOT enabled
  | 'org_level_disabled'          // NOT enabled
  | 'org_level_disabled_until'    // NOT enabled
  | 'seat_tier_level_disabled'    // NOT enabled
  | 'member_level_disabled'       // NOT enabled
  | 'seat_tier_zero_credit_limit' // NOT enabled
  | 'group_zero_credit_limit'     // NOT enabled
  | 'member_zero_credit_limit'    // NOT enabled
  | 'org_service_level_disabled'  // NOT enabled
  | 'org_service_zero_credit_limit' // NOT enabled
  | 'no_limits_configured'        // NOT enabled
  | 'unknown'                     // NOT enabled
```

---

## 14. Context Window Upgrade Suggestions (`contextWindowUpgradeCheck.ts`)

Checks if user's current model alias (`opus` or `sonnet`) can be upgraded to `[1m]` variant. Returns upgrade message strings:
- Warning context: `/model opus[1m]`
- Tip context: `"Tip: You have access to Opus 1M with 5x more context"`

---

## 15. Model Deprecation (`deprecation.ts`)

### 15.1 Deprecated Models Registry

| Model Pattern | Model Name | 1P Retirement | Bedrock | Vertex |
|--------------|-----------|---------------|---------|--------|
| `claude-3-opus` | Claude 3 Opus | Jan 5, 2026 | Jan 15, 2026 | Jan 5, 2026 |
| `claude-3-7-sonnet` | Claude 3.7 Sonnet | Feb 19, 2026 | Apr 28, 2026 | May 11, 2026 |
| `claude-3-5-haiku` | Claude 3.5 Haiku | Feb 19, 2026 | (not deprecated) | (not deprecated) |

### 15.2 Warning Format

```
WARNING: Claude 3.7 Sonnet will be retired on February 19, 2026. Consider switching to a newer model.
```

---

## 16. Legacy Model Remapping (`model.ts`)

### 16.1 Legacy Opus Models

```typescript
const LEGACY_OPUS_FIRSTPARTY = [
  'claude-opus-4-20250514',
  'claude-opus-4-1-20250805',
  'claude-opus-4-0',
  'claude-opus-4-1',
]
```

On first-party provider, these are silently remapped to `getDefaultOpusModel()` (currently Opus 4.6). Disabled with `CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP=1`.

---

## 17. Fast Mode (`src/utils/fastMode.ts`)

Opus 4.6 with accelerated inference (`fast-2025-rc1` beta header). Pricing: $30/$150 per Mtok (vs $5/$25 standard).

After 429/529 with long retry-after -> fast mode cooldown (10-30 min), switch to standard speed.

---

## 18. Effort Levels (`src/utils/effort.ts`)

| Level | Token Budget |
|-------|-------------|
| `low` | minimal thinking |
| `normal` | default |
| `high` | maximum thinking |
| numeric | explicit token count |

Resolution: `ANTHROPIC_THINKING_BUDGET_TOKENS` env -> app state -> per-model default.

---

## 19. 3P Model Support Overrides (`modelSupportOverrides.ts`)

### 19.1 Override Capabilities

```typescript
type ModelCapabilityOverride = 'effort' | 'max_effort' | 'thinking' | 'adaptive_thinking' | 'interleaved_thinking'
```

### 19.2 Configuration

3P providers can pin model defaults and declare supported capabilities:

| Env Var (Model) | Env Var (Capabilities) |
|----------------|----------------------|
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTED_CAPABILITIES` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTED_CAPABILITIES` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `ANTHROPIC_DEFAULT_HAIKU_MODEL_SUPPORTED_CAPABILITIES` |

Capabilities are comma-separated: e.g. `effort,thinking,adaptive_thinking`.

---

## 20. Model Validation (`validateModel.ts`)

### 20.1 Validation Flow

```
1. Empty check
2. Allowlist check (isModelAllowed)
3. Known alias check (always valid)
4. ANTHROPIC_CUSTOM_MODEL_OPTION match (pre-validated)
5. Cache check (validModelCache Map)
6. API probe: sideQuery with max_tokens=1, maxRetries=0
```

### 20.2 3P Fallback Suggestions

When a model is not found on 3P providers:
- `opus-4-6` -> suggests `opus41` string
- `sonnet-4-6` -> suggests `sonnet45` string
- `sonnet-4-5` -> suggests `sonnet40` string

---

## 21. Ant-Internal Model System (`antModels.ts`)

### 21.1 AntModel Type

```typescript
type AntModel = {
  alias: string                    // user-facing alias
  model: string                    // actual model ID (may be codename)
  label: string                    // display label
  description?: string            // model picker description
  defaultEffortValue?: number     // default effort budget
  defaultEffortLevel?: EffortLevel // default effort level
  contextWindow?: number          // custom context window size
  defaultMaxTokens?: number       // default max output tokens
  upperMaxTokensLimit?: number    // upper limit for max tokens
  alwaysOnThinking?: boolean      // adaptive thinking, rejects disabled
}
```

### 21.2 Feature Flag Source

Models loaded from GrowthBook feature flag `tengu_ant_model_override`, which provides:
- `defaultModel` — default model for ants
- `defaultModelEffortLevel` — default effort
- `defaultSystemPromptSuffix` — system prompt additions
- `antModels[]` — array of `AntModel` definitions
- `switchCallout` — model switch announcement config

---

## 22. Model Picker Options (`modelOptions.ts`)

### 22.1 Tier-Specific Option Lists

| User Tier | Options Shown |
|-----------|--------------|
| **Ant** | Default + ant model list + Opus 1M + Sonnet 4.6 + Sonnet 1M + Haiku 4.5 |
| **Max / Team Premium** | Default (Opus) + [Opus 1M if not merged] + Sonnet + [Sonnet 1M] + Haiku |
| **Pro / Team Standard / Enterprise** | Default (Sonnet) + [Sonnet 1M] + Opus (merged or separate + 1M) + Haiku |
| **PAYG 1P** | Default (Sonnet) + [Sonnet 1M] + Opus (merged or separate + 1M) + Haiku |
| **PAYG 3P** | Default (Sonnet 4.5) + Custom/Sonnet 4.6 + Custom/Opus 4.1+4.6+1M + Custom/Haiku |

### 22.2 Dynamic Option Injection

- `ANTHROPIC_CUSTOM_MODEL_OPTION` env var -> adds custom model with optional name/description
- `additionalModelOptionsCache` from bootstrap config -> server-pushed additional options
- Current/initial model -> auto-added if not already in list, with `getKnownModelOption()` providing upgrade hints

### 22.3 Upgrade Hints

When user has a specific older model pinned (e.g. `claude-opus-4-5-20251101`), the option shows: `"Newer version available - select Opus for Opus 4.6"`.

---

## 23. Complete Exported Functions Index

### `model.ts` (19 exports)

| Function | Purpose |
|----------|---------|
| `getSmallFastModel()` | Returns `ANTHROPIC_SMALL_FAST_MODEL` env or default Haiku |
| `isNonCustomOpusModel(model)` | Checks if model is one of the 4 Opus versions |
| `getUserSpecifiedModelSetting()` | Gets user's model from session/flag/env/settings with allowlist check |
| `getMainLoopModel()` | Resolves the session model (user-specified or default) |
| `getBestModel()` | Always returns default Opus |
| `getDefaultOpusModel()` | Provider-aware Opus default with env override |
| `getDefaultSonnetModel()` | Provider-aware Sonnet default (1P: 4.6, 3P: 4.5) with env override |
| `getDefaultHaikuModel()` | Provider-aware Haiku default with env override |
| `getRuntimeMainLoopModel(params)` | Per-turn model with plan-mode overrides |
| `getDefaultMainLoopModelSetting()` | Tier-based default model setting |
| `getDefaultMainLoopModel()` | Resolved default model name |
| `firstPartyNameToCanonical(name)` | Pure string-match canonical name extraction |
| `getCanonicalName(fullModelName)` | Full canonical name resolution (override + 1P canonical) |
| `getPublicModelDisplayName(model)` | Human-readable display name or null |
| `renderModelName(model)` | Display name with ant codename masking |
| `getPublicModelName(model)` | `"Claude {Name}"` for git commit trailers |
| `parseUserSpecifiedModel(input)` | Full alias/legacy/ant resolution pipeline |
| `resolveSkillModelOverride(skill, current)` | Carry [1m] suffix for skill model overrides |
| `normalizeModelStringForAPI(model)` | Strips `[1m]`/`[2m]` suffixes for API calls |
| `isLegacyModelRemapEnabled()` | Checks `CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP` |
| `isOpus1mMergeEnabled()` | Checks Opus/Opus-1M merge conditions |
| `getClaudeAiUserDefaultModelDescription(fast)` | Tier-aware description string |
| `getOpus46PricingSuffix(fastMode)` | Pricing suffix for Opus 4.6 display |
| `renderDefaultModelSetting(setting)` | Renders default model for display |
| `renderModelSetting(setting)` | Renders any model setting for display |
| `getMarketingNameForModel(modelId)` | Canonical-to-marketing-name mapping |
| `modelDisplayString(model)` | Full display string with tier context |

### Other Files (51+ exports total)

| File | Key Exports |
|------|-------------|
| `configs.ts` | `ALL_MODEL_CONFIGS`, `ModelKey`, `CanonicalModelId`, `CANONICAL_MODEL_IDS`, `CANONICAL_ID_TO_KEY` |
| `aliases.ts` | `MODEL_ALIASES`, `MODEL_FAMILY_ALIASES`, `isModelAlias()`, `isModelFamilyAlias()` |
| `modelOptions.ts` | `getModelOptions()`, `getDefaultOptionForUser()`, `ModelOption` |
| `modelAllowlist.ts` | `isModelAllowed()` |
| `modelCapabilities.ts` | `getModelCapability()`, `refreshModelCapabilities()` |
| `modelStrings.ts` | `getModelStrings()`, `ensureModelStringsInitialized()`, `resolveOverriddenModel()` |
| `agent.ts` | `getAgentModel()`, `getDefaultSubagentModel()`, `AGENT_MODEL_OPTIONS` |
| `antModels.ts` | `getAntModelOverrideConfig()`, `getAntModels()`, `resolveAntModel()` |
| `bedrock.ts` | `getBedrockInferenceProfiles()`, `createBedrockRuntimeClient()`, `getBedrockRegionPrefix()`, `applyBedrockRegionPrefix()` |
| `check1mAccess.ts` | `checkOpus1mAccess()`, `checkSonnet1mAccess()` |
| `contextWindowUpgradeCheck.ts` | `getUpgradeMessage()` |
| `deprecation.ts` | `getModelDeprecationWarning()` |
| `modelSupportOverrides.ts` | `get3PModelCapabilityOverride()` |
| `providers.ts` | `getAPIProvider()`, `getAPIProviderForStatsig()`, `isFirstPartyAnthropicBaseUrl()` |
| `validateModel.ts` | `validateModel()` |

---

## 24. Environment Variables Summary

| Variable | Used By | Purpose |
|----------|---------|---------|
| `ANTHROPIC_MODEL` | `model.ts` | Priority 3 model override |
| `ANTHROPIC_SMALL_FAST_MODEL` | `model.ts` | Small/fast model override |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `model.ts` | Default Opus override |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `model.ts` | Default Sonnet override |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `model.ts` | Default Haiku override |
| `ANTHROPIC_DEFAULT_*_MODEL_NAME` | `modelOptions.ts` | Custom model display name |
| `ANTHROPIC_DEFAULT_*_MODEL_DESCRIPTION` | `modelOptions.ts` | Custom model description |
| `ANTHROPIC_DEFAULT_*_MODEL_SUPPORTED_CAPABILITIES` | `modelSupportOverrides.ts` | 3P capability declarations |
| `ANTHROPIC_CUSTOM_MODEL_OPTION` | `modelOptions.ts`, `validateModel.ts` | Custom model in picker |
| `ANTHROPIC_CUSTOM_MODEL_OPTION_NAME` | `modelOptions.ts` | Custom model display name |
| `ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION` | `modelOptions.ts` | Custom model description |
| `ANTHROPIC_BASE_URL` | `providers.ts` | API base URL |
| `ANTHROPIC_BEDROCK_BASE_URL` | `bedrock.ts` | Bedrock endpoint override |
| `CLAUDE_CODE_USE_BEDROCK` | `providers.ts` | Enable Bedrock provider |
| `CLAUDE_CODE_USE_VERTEX` | `providers.ts` | Enable Vertex provider |
| `CLAUDE_CODE_USE_FOUNDRY` | `providers.ts` | Enable Foundry provider |
| `CLAUDE_CODE_SKIP_BEDROCK_AUTH` | `bedrock.ts` | Skip Bedrock authentication |
| `CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP` | `model.ts` | Disable Opus 4.0/4.1 remap |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `agent.ts` | Force all subagent models |
| `USER_TYPE` | Multiple | `'ant'` for Anthropic employees |
| `AWS_REGION` / `AWS_DEFAULT_REGION` | `bedrock.ts` | Bedrock region |
| `AWS_BEARER_TOKEN_BEDROCK` | `bedrock.ts` | Bedrock bearer token auth |

---

## 25. Architecture Diagram

```
                    User Input
                        |
          +-------------+-------------+
          v             v             v
    /model cmd     --model flag   ANTHROPIC_MODEL env
          |             |             |
          +-------------+-------------+
                        v
            getUserSpecifiedModelSetting()
                        |
                   isModelAllowed() <-- settings.availableModels
                        |
                        v
            parseUserSpecifiedModel()
              +---------+----------+
              v         v          v
         isModelAlias  isLegacy  resolveAntModel
              |         |          |
              +---------+----------+
                        v
              getModelStrings()[provider]
                        |
              +---------+----------+
              v         v          v
          firstParty  bedrock    vertex/foundry
              |    (profiles)       |
              +---------+----------+
                        v
            getRuntimeMainLoopModel()
              (plan mode overrides)
                        |
                        v
           normalizeModelStringForAPI()
              (strip [1m] suffix)
                        |
                        v
                   API Request
```
