"""
adapters — outbound integrations (LLM providers, external frameworks).

Per LLM-provider-neutrality (10-server-side-philosophy §原則 2): the
ONLY directories allowed to `import openai` / `import anthropic` /
`import agent_framework` are sibling provider dirs (azure_openai/,
anthropic/, openai/, maf/). The shared ABC lives in `_base/`.

Sprint 49.1: only `_base/ChatClient` ABC defined. Concrete adapters
in Sprint 49.3 (azure_openai) and onward.
"""
