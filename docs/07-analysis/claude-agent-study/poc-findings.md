# PoC Findings: AnthropicChatClient + MagenticBuilder Integration

> **Date**: 2026-03-22
> **Branch**: `poc/anthropic-chatclient` (git worktree)
> **Result**: ALL 5 STEPS PASS

---

## Verified API (vs Upgrade Plan Assumptions)

| # | Upgrade Plan Assumed | Actual API (RC4 installed) | Impact |
|---|---------------------|---------------------------|--------|
| 1 | Override `get_response()` | **ONE** method: `_inner_get_response(*, messages, stream, options)` — `stream=False` 返回 `Awaitable[ChatResponse]`，`stream=True` 返回 `ResponseStream` | 不是兩個 method |
| 2 | `from agent_framework import ChatMessage` | `from agent_framework import Message` — `Message(role='assistant', text='...')` | 所有 import 修正 |
| 3 | `Agent(chat_client=client, name=...)` | `Agent(client, name=...)` — positional 第一參數 | 構造方式不同 |
| 4 | `builder.with_standard_manager(agent=...)` | `MagenticBuilder(participants=..., manager_agent=...)` — 構造函數參數 | 注入方式完全不同 |
| 5 | `chat_options: ChatOptions` (required) | 參數是 `stream: bool` + `options: Mapping[str, Any]`（不是 `chat_options`） | 簽名完全不同 |
| 6 | Method is `async def` | **普通 `def`**（返回 Awaitable 或 ResponseStream，不是 coroutine） | 不是 async |
| 7 | `ChatResponseUpdate(text=...)` | `ChatResponseUpdate(contents=[Content(type='text', text=...)])` | 需要 Content 包裝 |

## MagenticBuilder 實際 API

### Constructor (RC4 installed)

```python
MagenticBuilder(
    participants: Sequence[SupportsAgentRun | Executor],  # REQUIRED, non-empty
    manager: MagenticManagerBase | None = None,
    manager_factory: Callable[[], MagenticManagerBase] | None = None,
    manager_agent: SupportsAgentRun | None = None,        # <-- inject here
    manager_agent_factory: Callable[[], SupportsAgentRun] | None = None,
    task_ledger: _MagenticTaskLedger | None = None,
    task_ledger_facts_prompt: str | None = None,
    task_ledger_plan_prompt: str | None = None,
    task_ledger_full_prompt: str | None = None,
    task_ledger_facts_update_prompt: str | None = None,
    task_ledger_plan_update_prompt: str | None = None,
    progress_ledger_prompt: str | None = None,
    final_answer_prompt: str | None = None,
    max_stall_count: int = 3,
    max_reset_count: int | None = None,
    max_round_count: int | None = None,
    enable_plan_review: bool = False,
    checkpoint_storage: CheckpointStorage | None = None,
    intermediate_outputs: bool = False,
)
```

### Only 3 Public Methods

```python
builder.build()                          # -> Workflow
builder.with_checkpointing(storage)      # -> MagenticBuilder
builder.with_plan_review(enable=True)    # -> MagenticBuilder
```

**NO** `with_standard_manager()` in RC4.

## AnthropicChatClient Correct Implementation

```python
from agent_framework import (
    BaseChatClient, ChatResponse, ChatResponseUpdate, Content, Message, ResponseStream,
)

class AnthropicChatClient(BaseChatClient):
    def __init__(self, *, model, api_key=None, thinking_config=None, max_tokens=16000, **kwargs):
        super().__init__(**kwargs)  # MUST call super
        self._client = AsyncAnthropic(api_key=api_key)
        ...

    # ONE method, NOT async — returns Awaitable or ResponseStream based on stream param
    def _inner_get_response(self, *, messages, stream, options, **kwargs):
        if stream:
            return self._build_response_stream(self._stream_anthropic(messages, options))
        else:
            return self._call_anthropic(messages, options)

    async def _call_anthropic(self, messages, options) -> ChatResponse:
        # Convert Message[] -> Anthropic format -> call API -> return ChatResponse
        ...

    async def _stream_anthropic(self, messages, options) -> AsyncIterable[ChatResponseUpdate]:
        # Stream -> yield ChatResponseUpdate(contents=[Content(type='text', text=chunk)])
        ...
```

### Key Differences from Initial poc-findings.md (V1)

| V1 (incorrect) | V2 (correct, verified by working code) |
|----------------|---------------------------------------|
| Two abstract methods | **ONE** method with `stream` param |
| `async def _inner_get_response` | **`def`** (not async) |
| `chat_options=None` | `stream: bool, options: Mapping` |
| `ChatResponseUpdate(text=...)` | `ChatResponseUpdate(contents=[Content(type='text', text=...)])` |

### Limitation: No Function Calling Support

AnthropicChatClient does NOT support MAF's function invoking system. Agents using
this client **cannot use @tool decorated functions** in GroupChatBuilder.
Azure OpenAI's `AzureOpenAIResponsesClient` supports function calling natively.

To add function calling support, AnthropicChatClient needs:
1. `FUNCTION_INVOKING_CHAT_CLIENT_MARKER` class attribute
2. Handle `tools` in options → convert to Anthropic tool format
3. Parse tool_use blocks in response → return as MAF Content(type='function_call')

## Agent Creation

```python
from agent_framework import Agent

# CORRECT — positional first arg
agent = Agent(
    anthropic_chat_client,    # positional: client
    name="MagenticManager",
    instructions="You are a strategic orchestrator...",
)
```

## Full Integration Pattern

```python
from agent_framework import Agent
from agent_framework.orchestrations import MagenticBuilder

# 1. Create ChatClient
manager_client = AnthropicChatClient(model="claude-opus-4-6", thinking_config=...)

# 2. Create Agent
manager_agent = Agent(manager_client, name="Manager", instructions="...")

# 3. Create Workers
worker1 = Agent(worker_client, name="Worker-1", instructions="...")

# 4. Build MagenticOne workflow — inject via constructor
builder = MagenticBuilder(
    participants=[worker1, worker2],
    manager_agent=manager_agent,          # <-- inject here
    max_stall_count=3,
    max_round_count=10,
    enable_plan_review=True,
)
workflow = builder.build()
```

## Impact on Phase 44 Plan

1. **Sprint 151 S151-1**: build() 修復方式完全不同 — 不是加 `with_standard_manager()` 呼叫，而是在 `MagenticBuilder()` 構造時傳入 `manager_agent=`
2. **Sprint 151 S151-2**: AnthropicChatClient 已驗證可行，但需用正確的 abstract methods
3. **Sprint 152 S152-1**: `build_with_model_selection()` 的實作方式需調整 — 重新構造 `MagenticBuilder` 而非用 with_ 方法
4. **LOC 估算**: 大致不變（~150 LOC for ChatClient, ~120 LOC for Registry）

## Test Results

```
POST /poc/manager-model/test-chatclient?model=claude-haiku-4-5-20251001
  ✅ instantiate (158ms)
  ✅ isinstance_check (BaseChatClient: true)
  ✅ get_response (901ms) → "OK"

POST /poc/manager-model/test-magentic-injection?model=claude-haiku-4-5-20251001
  ✅ create_chatclient
  ✅ create_agent (name: "PoC-Manager")
  ✅ create_dummy_worker
  ✅ create_magentic_builder_with_manager
  ✅ build → Workflow
```
