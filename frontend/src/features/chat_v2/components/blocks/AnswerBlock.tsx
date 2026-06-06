/* eslint-disable no-restricted-syntax -- production-only block: the mockup's block set
   (thinking / tool / verification / subagent_fork) has no assistant-answer block, so the
   final LLM text answer must still render for the chat to be usable. Inline styles use
   only layout/typography (no color literal) and inherit the mockup .turn-body color. */
/**
 * File: frontend/src/features/chat_v2/components/blocks/AnswerBlock.tsx
 * Purpose: Renders the agent's final text answer (llm_response.content) inside an AgentTurn.
 * Category: Frontend / chat_v2 / components / blocks
 * Scope: 2026-06-06 honest testing surface (CHANGE-054)
 *
 * Description:
 *   The Sprint 57.21 Block union mirrored the mockup (thinking / tool / verification /
 *   subagent_fork) — which had NO assistant-answer block. As a result a plain Q&A turn
 *   (the model answers directly, no tool call) rendered an empty turn body, so the agent's
 *   actual answer was invisible (the root of "can't see the LLM output"). This block
 *   renders the final content as readable, whitespace-preserving prose. Inherits the
 *   mockup .turn-body text color (no color literal). Rich markdown render deferred
 *   (AD-ChatV2-Answer-Markdown-Phase2).
 *
 * Created: 2026-06-06 (CHANGE-054)
 *
 * Related:
 *   - ../../types.ts (AnswerBlock)
 *   - ./Block.tsx (dispatcher — exhaustive switch)
 *   - ../../store/chatStore.ts (llm_response case emits this from ev.data.content)
 */

import type { AnswerBlock as AnswerBlockType } from "../../types";

export function AnswerBlock({ block }: { block: AnswerBlockType }): JSX.Element {
  return (
    <div
      data-testid="answer-block"
      style={{ whiteSpace: "pre-wrap", fontSize: 13.5, lineHeight: 1.55, margin: "4px 0" }}
    >
      {block.text}
    </div>
  );
}
