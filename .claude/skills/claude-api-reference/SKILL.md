---
name: claude-api-reference
description: "Claude API development reference guide. Use when developing Claude API applications for Messages API, Vision, PDF processing, Tool Use, Streaming, Managed Agents, and more. Triggers: (1) Claude API integration development, (2) Image or PDF file processing, (3) Tool Use or Function Calling implementation, (4) Streaming or Batch processing setup, (5) Any Claude SDK development questions. Updated: 2026-04-11"
---

# Claude API Reference Skill

This skill provides essential knowledge and best practices for Claude API development.

**Anthropic Python SDK**: `anthropic==0.87.0` (2026-03-31)
**API Version**: `2023-06-01` (unchanged)

## Quick Start

```python
from anthropic import Anthropic

client = Anthropic()  # Automatically reads ANTHROPIC_API_KEY from environment
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}]
)
print(message.content[0].text)
```

## Model Selection (as of 2026-04)

| Model | API ID | Context | Max Output | Best For |
|-------|--------|---------|------------|----------|
| **Claude Opus 4.6** | `claude-opus-4-6` | 1M tokens | 128k tokens | Highest intelligence, complex reasoning |
| **Claude Sonnet 4.6** | `claude-sonnet-4-6` | 1M tokens (beta) | 64k tokens | Balanced speed/intelligence, agentic tasks |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 200k tokens | 8k tokens | Fastest speed, near-frontier |
| Claude Opus 4.5 | `claude-opus-4-5` | 200k tokens | 32k tokens | Previous gen, still available |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | 200k tokens | 16k tokens | Previous gen, still available |

## Pricing (per 1M tokens)

| Model | Input | Output |
|-------|-------|--------|
| Opus 4.6 | $5 | $25 |
| Sonnet 4.6 | $3 | $15 |
| Haiku 4.5 | $1 | $5 |

## Core API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/messages` | Primary conversation API |
| `POST /v1/messages/batches` | Batch processing (50% discount) |
| `POST /v1/messages/count_tokens` | Token counting |
| `GET /v1/models` | List available models |
| `POST /v1/files` | File upload (GA) |
| **`POST /v1/agents`** | **Managed Agents (Beta)** |
| **`POST /v1/sessions`** | **Agent Sessions (Beta)** |
| **`POST /v1/skills`** | **Skills API (New)** |

## Required Headers

```
x-api-key: YOUR_API_KEY
anthropic-version: 2023-06-01
content-type: application/json
```

### 2026 Beta Headers

| Header | Purpose |
|--------|---------|
| `output-300k-2026-03-24` | Extended output (long-form content, large code) |
| `managed-agents-2026-04-01` | Managed Agents endpoint access |

## Managed Agents (New — Public Beta)

Fully managed agent harness with sandbox, built-in tools, SSE streaming:

```python
# Requires beta header: managed-agents-2026-04-01
agent = client.agents.create(
    model="claude-sonnet-4-6",
    instructions="You are a helpful assistant.",
    tools=["Read", "Write", "Bash"],
)

session = client.sessions.create(agent_id=agent.id)
response = client.sessions.messages.create(
    session_id=session.id,
    messages=[{"role": "user", "content": "Analyze this codebase"}],
)
```

## Tool Use / Function Calling

```python
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[{
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g. San Francisco, CA"
                }
            },
            "required": ["location"]
        }
    }],
    messages=[{"role": "user", "content": "What's the weather in Taipei?"}]
)
```

### Tool Helpers (Beta — New in SDK 0.87.0)

Type-safe input validation + automatic tool runner:

```python
# SDK now provides helpers for type-safe tool execution
# See anthropic SDK docs for tool_helpers module
```

### Server-side Tools (New)

Skills that run on Anthropic servers: Excel, PowerPoint, Word, PDF generation.

## File Handling

### PDF Processing

```python
import base64

with open("document.pdf", "rb") as f:
    pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data
                }
            },
            {"type": "text", "text": "Analyze the key points of this document"}
        ]
    }]
)
```

### Image Processing

```python
# Base64 method
{
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/png",  # image/jpeg, image/gif, image/webp
        "data": image_base64
    }
}

# URL method
{
    "type": "image",
    "source": {
        "type": "url",
        "url": "https://example.com/image.jpg"
    }
}
```

## Streaming

```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a story"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

## Batch Processing (50% Discount)

```python
batch = client.messages.batches.create(
    requests=[
        {
            "custom_id": "request-1",
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "Hello"}]
            }
        }
    ]
)
```

## Limits

| Limit Type | Value |
|------------|-------|
| Standard request size | 32 MB |
| Batch API | 256 MB |
| Files API | 500 MB |
| PDF pages | 100 pages |
| Single image | 8000x8000 px |
| Multi-image per image | 2000x2000 px |
| Max images per request | 20 images |
| Message limit | 100,000 per request |

## Extended Thinking

```python
message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16384,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    messages=[{"role": "user", "content": "Solve this complex problem..."}]
)
```

## Official Resources

- Documentation: https://docs.anthropic.com
- Python SDK: https://github.com/anthropics/anthropic-sdk-python
- Cookbook: https://github.com/anthropics/anthropic-cookbook
- Quickstarts: https://github.com/anthropics/anthropic-quickstarts
- Agent SDK: https://github.com/anthropics/claude-agent-sdk-python

## Detailed References

- **PDF/Image processing**: `references/file_handling.md`
- **Tool Use**: `references/tool_use.md`
- **Advanced features**: `references/advanced_features.md`

## Version History

- 2026-04-11: Updated to SDK 0.87.0, added Opus/Sonnet 4.6, Managed Agents, Skills API
- 2026-01-09: Initial reference with Claude 4.5 models
