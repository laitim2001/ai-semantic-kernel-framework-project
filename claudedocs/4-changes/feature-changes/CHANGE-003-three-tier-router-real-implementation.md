# CHANGE-003: Three-Tier Router Real Implementation

## Change Overview

| Field | Value |
|-------|-------|
| **Change ID** | CHANGE-003 |
| **Date** | 2026-01-29 |
| **Type** | Feature Enhancement |
| **Priority** | High |
| **Status** | Completed |
| **Related Sprint** | Phase 28 Enhancement |

## Summary

Switch the three-tier intent routing system from Mock implementation to real implementation, enabling actual pattern matching, semantic routing with Azure OpenAI embeddings, and LLM classification with Claude Haiku.

## Problem Statement

The existing intent routing system was using `MockBusinessIntentRouter` which:
- Used keyword-based classification instead of real LLM
- Did not utilize vector similarity for semantic routing
- Showed "Mock classification based on keywords" in reasoning
- Could not properly identify complex intents like system command execution

## Solution

### 1. SemanticRouter Azure OpenAI Support

Modified `semantic_router/router.py` to support Azure OpenAI Encoder:

```python
# New parameters added to SemanticRouter.__init__()
encoder_type: Literal["openai", "azure"] = "openai"
azure_api_key: Optional[str] = None
azure_endpoint: Optional[str] = None
azure_deployment_name: Optional[str] = None
azure_api_version: str = "2024-02-15-preview"

# New method _create_encoder() to select appropriate encoder
def _create_encoder(self) -> Optional[Any]:
    if self.encoder_type == "azure":
        return _AzureOpenAIEncoder(
            api_key=self._azure_api_key,
            azure_endpoint=self._azure_endpoint,
            deployment_name=self._azure_deployment_name,
            api_version=self._azure_api_version,
        )
    else:
        return _OpenAIEncoder(**encoder_kwargs)
```

### 2. Intent Routes Configuration

Modified `intent_routes.py` to use real router:

```python
# Configuration flag
USE_REAL_ROUTER = os.getenv("USE_REAL_ROUTER", "true").lower() == "true"

# Dynamic router selection in get_router()
if USE_REAL_ROUTER and anthropic_key:
    _router_instance = create_router(
        pattern_rules_path=rules_path,
        semantic_routes=semantic_routes,
        llm_api_key=anthropic_key,
        config=config,
    )
else:
    _router_instance = create_mock_router(config=config)
```

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/src/integrations/orchestration/intent_router/semantic_router/router.py` | Modified | Added Azure OpenAI Encoder support |
| `backend/src/api/v1/orchestration/intent_routes.py` | Modified | Switched to real three-tier router |

## Configuration Requirements

### Environment Variables

```bash
# Required for LLM Classifier (Layer 3)
ANTHROPIC_API_KEY=sk-ant-...

# Required for Semantic Router (Layer 2) with Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002  # Optional, has default

# Optional
USE_REAL_ROUTER=true  # Default: true
```

### Azure OpenAI Requirements

- An Azure OpenAI resource with embedding model deployed
- Deployment name: `text-embedding-ada-002` (or configure via env var)

## Expected Behavior After Change

### Routing Decision Display

| Field | Before (Mock) | After (Real) |
|-------|---------------|--------------|
| Routing Layer | Always "llm" | "pattern", "semantic", or "llm" |
| Reasoning | "Mock classification based on keywords" | Actual analysis from matched layer |
| Processing Time | < 1ms | Pattern: <10ms, Semantic: <100ms, LLM: <2000ms |

### Test Cases

| Input | Expected Intent | Expected Layer |
|-------|-----------------|----------------|
| "ETL Pipeline 今天跑失敗了" | INCIDENT / etl_failure | pattern |
| "我需要申請一個新帳號" | REQUEST / account_creation | pattern or semantic |
| "請執行pwd指令" | UNKNOWN or QUERY | llm |
| "系統很慢，效能問題" | INCIDENT / performance | pattern or semantic |

## Rollback Plan

To revert to mock router:

```bash
# Set environment variable
USE_REAL_ROUTER=false
```

Or remove `ANTHROPIC_API_KEY` from environment.

## Testing Verification

1. Restart backend service
2. Check logs for "Real router initialized" message
3. Test with various inputs on /chat page
4. Verify Orchestration panel shows correct routing layer

## Related Documentation

- `docs/07-analysis/MAF-Claude-Hybrid-Architecture-V2.md` - Architecture overview
- `backend/src/integrations/orchestration/intent_router/pattern_matcher/rules.yaml` - Pattern rules (34 rules)
- `backend/src/integrations/orchestration/intent_router/semantic_router/routes.py` - Semantic routes (15 routes)
