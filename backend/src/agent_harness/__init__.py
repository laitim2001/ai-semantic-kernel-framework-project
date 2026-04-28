"""
agent_harness — V2 11+1 category agent harness.

Each category is an isolated subpackage; cross-category types live in
`_contracts/`. Import order:

    from agent_harness._contracts import Message, ToolSpec, LoopState, ...
    from agent_harness.orchestrator_loop import AgentLoop
    from agent_harness.tools import ToolRegistry, ToolExecutor
    ...

CRITICAL: This package and its subpackages MUST NEVER import LLM SDKs
directly (openai / anthropic). Use `adapters/_base/chat_client.ChatClient`
ABC instead. CI lint enforces this in Sprint 49.4.
"""
