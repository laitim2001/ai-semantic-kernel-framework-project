# =============================================================================
# IPA Platform - Few-shot Learner
# =============================================================================
# Sprint 80: S80-1 - Few-shot 學習系統 (8 pts)
#
# This module provides the core Few-shot learning functionality,
# dynamically enhancing prompts with historical case examples.
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .types import (
    Case,
    CaseCategory,
    LearningConfig,
    LearningEffectiveness,
    LearningResult,
    SimilarityResult,
    DEFAULT_LEARNING_CONFIG,
)
from .case_extractor import CaseExtractor
from .similarity import SimilarityCalculator


logger = logging.getLogger(__name__)


class FewShotLearner:
    """
    Few-shot learning system for enhancing AI decision-making.

    Uses historical cases to provide relevant examples that improve
    the quality of AI-generated plans and decisions.
    """

    def __init__(
        self,
        embedding_service: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        config: Optional[LearningConfig] = None,
    ):
        """
        Initialize the Few-shot learner.

        Args:
            embedding_service: EmbeddingService for semantic similarity.
            memory_manager: UnifiedMemoryManager for case storage.
            config: Learning configuration.
        """
        self.config = config or DEFAULT_LEARNING_CONFIG
        self._embedding_service = embedding_service
        self._memory_manager = memory_manager

        self._case_extractor = CaseExtractor(config=config)
        self._similarity_calculator = SimilarityCalculator(config=config)

        # Track learning results for effectiveness measurement
        self._learning_history: Dict[str, LearningResult] = {}
        self._effectiveness_records: List[LearningEffectiveness] = []

        self._initialized = False

    async def initialize(
        self,
        embedding_service: Any,
        memory_manager: Any,
    ) -> None:
        """
        Initialize the learner with required services.

        Args:
            embedding_service: EmbeddingService instance.
            memory_manager: UnifiedMemoryManager instance.
        """
        self._embedding_service = embedding_service
        self._memory_manager = memory_manager

        await self._case_extractor.initialize(memory_manager)

        self._initialized = True
        logger.info("FewShotLearner initialized")

    def _ensure_initialized(self) -> None:
        """Ensure the learner is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "FewShotLearner not initialized. Call initialize() first."
            )

    async def get_similar_cases(
        self,
        event_description: str,
        affected_systems: List[str],
        category: Optional[CaseCategory] = None,
        top_k: Optional[int] = None,
    ) -> List[SimilarityResult]:
        """
        Find similar historical cases for an event.

        Args:
            event_description: Description of the current event.
            affected_systems: List of affected systems.
            category: Optional category filter.
            top_k: Number of cases to return.

        Returns:
            List of similar cases with scores.
        """
        self._ensure_initialized()

        top_k = top_k or self.config.top_k_cases

        try:
            # Generate embedding for the event description
            event_embedding = await self._embedding_service.embed_text(
                event_description
            )

            # Extract cases from memory
            cases = await self._case_extractor.extract_from_memory(
                query=event_description,
                category=category,
                limit=top_k * 3,  # Get more for filtering
            )

            if not cases:
                logger.info("No historical cases found")
                return []

            # Generate embeddings for cases without them
            for case in cases:
                if not case.embedding:
                    case.embedding = await self._embedding_service.embed_text(
                        case.description
                    )

            # Rank cases by similarity
            results = self._similarity_calculator.rank_cases(
                cases=cases,
                query_embedding=event_embedding,
                query_systems=affected_systems,
                top_k=top_k,
            )

            logger.info(
                f"Found {len(results)} similar cases for event "
                f"(top score: {results[0].combined_score:.3f if results else 0})"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to get similar cases: {e}")
            return []

    async def enhance_prompt(
        self,
        base_prompt: str,
        event_description: str,
        affected_systems: List[str],
        category: Optional[CaseCategory] = None,
    ) -> LearningResult:
        """
        Enhance a prompt with relevant historical case examples.

        Args:
            base_prompt: The original prompt to enhance.
            event_description: Description of the current event.
            affected_systems: List of affected systems.
            category: Optional category filter.

        Returns:
            LearningResult with enhanced prompt and used cases.
        """
        self._ensure_initialized()

        enhancement_id = str(uuid4())

        try:
            # Get similar cases
            similar_results = await self.get_similar_cases(
                event_description=event_description,
                affected_systems=affected_systems,
                category=category,
                top_k=self.config.max_examples_in_prompt,
            )

            if not similar_results:
                # No cases found, return original prompt
                result = LearningResult(
                    original_prompt=base_prompt,
                    enhanced_prompt=base_prompt,
                    cases_used=[],
                    enhancement_id=enhancement_id,
                )
                self._learning_history[enhancement_id] = result
                return result

            # Extract cases from results
            cases = [r.case for r in similar_results]

            # Build enhanced prompt
            enhanced_prompt = self._build_enhanced_prompt(
                base_prompt=base_prompt,
                cases=cases,
            )

            result = LearningResult(
                original_prompt=base_prompt,
                enhanced_prompt=enhanced_prompt,
                cases_used=cases,
                enhancement_id=enhancement_id,
            )

            # Store for effectiveness tracking
            self._learning_history[enhancement_id] = result

            logger.info(
                f"Enhanced prompt with {len(cases)} cases "
                f"(enhancement_id: {enhancement_id})"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to enhance prompt: {e}")
            # Return original prompt on error
            return LearningResult(
                original_prompt=base_prompt,
                enhanced_prompt=base_prompt,
                cases_used=[],
                enhancement_id=enhancement_id,
            )

    def _build_enhanced_prompt(
        self,
        base_prompt: str,
        cases: List[Case],
    ) -> str:
        """
        Build an enhanced prompt with case examples.

        Args:
            base_prompt: The original prompt.
            cases: List of relevant cases.

        Returns:
            Enhanced prompt string.
        """
        if not cases:
            return base_prompt

        # Build case examples section
        examples = []
        for i, case in enumerate(cases, 1):
            example = self._format_case_example(case, i)
            examples.append(example)

        examples_section = "\n\n".join(examples)

        # Build the enhanced prompt
        enhanced = f"""{base_prompt}

## 參考歷史案例

以下是與當前情況相似的歷史案例，供參考：

{examples_section}

## 注意事項

請參考以上歷史案例的處理方式，結合當前情況制定解決方案。不要直接複製歷史案例的步驟，而是根據實際情況進行調整。"""

        return enhanced

    def _format_case_example(self, case: Case, index: int) -> str:
        """Format a case as an example for the prompt."""
        parts = [f"### 案例 {index}: {case.title}"]

        parts.append(f"**描述**: {case.description[:500]}")

        if case.affected_systems:
            systems = ", ".join(case.affected_systems)
            parts.append(f"**受影響系統**: {systems}")

        if case.root_cause and self.config.include_lessons_learned:
            parts.append(f"**根本原因**: {case.root_cause}")

        if case.resolution_steps and self.config.include_resolution_steps:
            steps = "\n".join(
                [f"  {i+1}. {s}" for i, s in enumerate(case.resolution_steps[:5])]
            )
            parts.append(f"**解決步驟**:\n{steps}")

        parts.append(f"**結果**: {case.outcome.value}")

        if case.lessons_learned and self.config.include_lessons_learned:
            parts.append(f"**經驗教訓**: {case.lessons_learned}")

        return "\n".join(parts)

    async def track_effectiveness(
        self,
        enhancement_id: str,
        decision_id: str,
        was_successful: bool,
        quality_improvement: Optional[float] = None,
        feedback: Optional[str] = None,
    ) -> LearningEffectiveness:
        """
        Track the effectiveness of a learning enhancement.

        Args:
            enhancement_id: ID of the enhancement to track.
            decision_id: ID of the decision made.
            was_successful: Whether the decision was successful.
            quality_improvement: Quality improvement score (-1.0 to 1.0).
            feedback: Optional feedback text.

        Returns:
            LearningEffectiveness record.
        """
        record = LearningEffectiveness(
            enhancement_id=enhancement_id,
            decision_id=decision_id,
            was_successful=was_successful,
            quality_improvement=quality_improvement,
            feedback=feedback,
        )

        self._effectiveness_records.append(record)

        # Update case quality scores based on effectiveness
        if enhancement_id in self._learning_history:
            learning_result = self._learning_history[enhancement_id]
            await self._update_case_quality(
                cases=learning_result.cases_used,
                was_successful=was_successful,
                quality_improvement=quality_improvement,
            )

        logger.info(
            f"Tracked effectiveness for enhancement {enhancement_id}: "
            f"success={was_successful}"
        )

        return record

    async def _update_case_quality(
        self,
        cases: List[Case],
        was_successful: bool,
        quality_improvement: Optional[float],
    ) -> None:
        """Update case quality scores based on usage outcome."""
        for case in cases:
            # Simple quality update: increase if successful, decrease if not
            if was_successful:
                case.quality_score = min(1.0, case.quality_score + 0.05)
            else:
                case.quality_score = max(0.0, case.quality_score - 0.02)

            # Update in cache
            self._case_extractor._case_cache[case.id] = case

    def get_effectiveness_stats(self) -> Dict[str, Any]:
        """
        Get statistics on learning effectiveness.

        Returns:
            Dictionary with effectiveness statistics.
        """
        if not self._effectiveness_records:
            return {
                "total_enhancements": 0,
                "success_rate": 0.0,
                "avg_quality_improvement": 0.0,
            }

        total = len(self._effectiveness_records)
        successes = sum(1 for r in self._effectiveness_records if r.was_successful)
        improvements = [
            r.quality_improvement
            for r in self._effectiveness_records
            if r.quality_improvement is not None
        ]

        return {
            "total_enhancements": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_quality_improvement": (
                sum(improvements) / len(improvements) if improvements else 0.0
            ),
            "total_cases_used": sum(
                len(self._learning_history.get(r.enhancement_id, LearningResult(
                    original_prompt="", enhanced_prompt="", cases_used=[], enhancement_id=""
                )).cases_used)
                for r in self._effectiveness_records
                if r.enhancement_id in self._learning_history
            ),
        }

    def get_learning_result(self, enhancement_id: str) -> Optional[LearningResult]:
        """Get a learning result by ID."""
        return self._learning_history.get(enhancement_id)

    async def store_successful_resolution(
        self,
        event_description: str,
        resolution_steps: List[str],
        affected_systems: List[str],
        root_cause: Optional[str] = None,
        lessons_learned: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Case:
        """
        Store a successful resolution as a new case for future learning.

        Args:
            event_description: Description of the event.
            resolution_steps: Steps taken to resolve.
            affected_systems: Systems affected.
            root_cause: Root cause analysis.
            lessons_learned: Lessons learned.
            user_id: User who resolved.

        Returns:
            Created Case object.
        """
        self._ensure_initialized()

        from .types import CaseOutcome

        case = await self._case_extractor.create_case_from_resolution(
            event_description=event_description,
            resolution_steps=resolution_steps,
            outcome=CaseOutcome.SUCCESS,
            affected_systems=affected_systems,
            root_cause=root_cause,
            lessons_learned=lessons_learned,
            user_id=user_id,
        )

        logger.info(f"Stored successful resolution as case: {case.id}")

        return case

    def clear_history(self) -> None:
        """Clear learning history and effectiveness records."""
        self._learning_history.clear()
        self._effectiveness_records.clear()
        self._case_extractor.clear_cache()
        logger.info("Learning history cleared")
