# =============================================================================
# IPA Platform - Case Extractor
# =============================================================================
# Sprint 80: S80-1 - Few-shot 學習系統 (8 pts)
#
# This module extracts historical cases from the memory system
# for use in Few-shot learning.
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .types import (
    Case,
    CaseCategory,
    CaseMetadata,
    CaseOutcome,
    LearningConfig,
    DEFAULT_LEARNING_CONFIG,
)


logger = logging.getLogger(__name__)


class CaseExtractor:
    """
    Extracts historical cases from memory for Few-shot learning.

    Works with the mem0-based memory system to find relevant cases
    and convert them to the Case format.
    """

    def __init__(
        self,
        memory_manager: Optional[Any] = None,
        config: Optional[LearningConfig] = None,
    ):
        """
        Initialize the case extractor.

        Args:
            memory_manager: UnifiedMemoryManager instance.
            config: Learning configuration.
        """
        self._memory_manager = memory_manager
        self.config = config or DEFAULT_LEARNING_CONFIG
        self._case_cache: Dict[str, Case] = {}

    async def initialize(self, memory_manager: Any) -> None:
        """
        Initialize with memory manager.

        Args:
            memory_manager: UnifiedMemoryManager instance.
        """
        self._memory_manager = memory_manager
        logger.info("CaseExtractor initialized with memory manager")

    def _ensure_initialized(self) -> None:
        """Ensure the extractor is initialized."""
        if self._memory_manager is None:
            raise RuntimeError(
                "CaseExtractor not initialized. Call initialize() first."
            )

    async def extract_from_memory(
        self,
        query: str,
        user_id: Optional[str] = None,
        category: Optional[CaseCategory] = None,
        limit: int = 20,
    ) -> List[Case]:
        """
        Extract cases from memory based on a query.

        Args:
            query: Search query to find relevant cases.
            user_id: Optional user ID filter.
            category: Optional category filter.
            limit: Maximum cases to return.

        Returns:
            List of extracted Case objects.
        """
        self._ensure_initialized()

        try:
            # Import memory types
            from src.integrations.memory import MemoryType

            # Search memory for event resolutions
            results = await self._memory_manager.search(
                query=query,
                user_id=user_id or "",
                memory_types=[MemoryType.EVENT_RESOLUTION, MemoryType.BEST_PRACTICE],
                limit=limit * 2,  # Get more to filter
            )

            cases = []
            for result in results:
                memory = result.memory

                # Convert memory to case
                case = self._memory_to_case(memory)
                if case:
                    # Apply category filter
                    if category and case.category != category:
                        continue

                    # Apply quality filter
                    if case.quality_score >= self.config.min_quality_score:
                        cases.append(case)
                        self._case_cache[case.id] = case

            logger.info(
                f"Extracted {len(cases)} cases from memory for query: {query[:50]}..."
            )
            return cases[:limit]

        except Exception as e:
            logger.error(f"Failed to extract cases from memory: {e}")
            return []

    def _memory_to_case(self, memory: Any) -> Optional[Case]:
        """
        Convert a memory record to a Case.

        Args:
            memory: MemoryRecord from the memory system.

        Returns:
            Case object or None if conversion fails.
        """
        try:
            # Parse memory content
            content = memory.content

            # Extract structured data if available
            metadata = memory.metadata

            # Determine category from tags or content
            category = self._infer_category(content, metadata.tags)

            # Determine outcome (default to success for stored resolutions)
            outcome = CaseOutcome.SUCCESS

            # Extract affected systems from metadata or content
            affected_systems = self._extract_affected_systems(content, metadata)

            # Create case
            case = Case(
                id=memory.id,
                title=self._extract_title(content),
                description=content,
                category=category,
                outcome=outcome,
                affected_systems=affected_systems,
                root_cause=metadata.custom.get("root_cause"),
                resolution_steps=self._extract_resolution_steps(content),
                lessons_learned=metadata.custom.get("lessons_learned"),
                quality_score=metadata.importance,
                metadata=CaseMetadata(
                    source=metadata.source,
                    event_id=metadata.event_id,
                    tags=metadata.tags,
                    custom=metadata.custom,
                ),
                created_at=memory.created_at,
            )

            return case

        except Exception as e:
            logger.warning(f"Failed to convert memory to case: {e}")
            return None

    def _infer_category(self, content: str, tags: List[str]) -> CaseCategory:
        """Infer case category from content and tags."""
        content_lower = content.lower()
        tags_lower = [t.lower() for t in tags]

        # Check tags first
        tag_category_map = {
            "incident": CaseCategory.INCIDENT_RESOLUTION,
            "performance": CaseCategory.PERFORMANCE_OPTIMIZATION,
            "security": CaseCategory.SECURITY_RESPONSE,
            "deployment": CaseCategory.DEPLOYMENT_ISSUE,
            "config": CaseCategory.CONFIGURATION_CHANGE,
            "configuration": CaseCategory.CONFIGURATION_CHANGE,
            "support": CaseCategory.USER_SUPPORT,
            "maintenance": CaseCategory.SYSTEM_MAINTENANCE,
        }

        for tag in tags_lower:
            for key, category in tag_category_map.items():
                if key in tag:
                    return category

        # Check content
        content_category_map = {
            "incident": CaseCategory.INCIDENT_RESOLUTION,
            "outage": CaseCategory.INCIDENT_RESOLUTION,
            "error": CaseCategory.INCIDENT_RESOLUTION,
            "slow": CaseCategory.PERFORMANCE_OPTIMIZATION,
            "performance": CaseCategory.PERFORMANCE_OPTIMIZATION,
            "latency": CaseCategory.PERFORMANCE_OPTIMIZATION,
            "security": CaseCategory.SECURITY_RESPONSE,
            "vulnerability": CaseCategory.SECURITY_RESPONSE,
            "deploy": CaseCategory.DEPLOYMENT_ISSUE,
            "release": CaseCategory.DEPLOYMENT_ISSUE,
            "config": CaseCategory.CONFIGURATION_CHANGE,
            "setting": CaseCategory.CONFIGURATION_CHANGE,
        }

        for keyword, category in content_category_map.items():
            if keyword in content_lower:
                return category

        return CaseCategory.OTHER

    def _extract_affected_systems(self, content: str, metadata: Any) -> List[str]:
        """Extract affected systems from content and metadata."""
        systems = []

        # Check metadata custom fields
        if hasattr(metadata, "custom") and metadata.custom:
            if "affected_systems" in metadata.custom:
                systems.extend(metadata.custom["affected_systems"])
            if "systems" in metadata.custom:
                systems.extend(metadata.custom["systems"])

        # Extract from content (simple heuristic)
        common_systems = [
            "database", "redis", "postgresql", "mongodb",
            "api", "gateway", "load balancer",
            "kubernetes", "docker", "container",
            "network", "dns", "ssl",
            "authentication", "authorization",
            "storage", "s3", "blob",
            "queue", "rabbitmq", "kafka",
        ]

        content_lower = content.lower()
        for system in common_systems:
            if system in content_lower and system not in systems:
                systems.append(system)

        return systems

    def _extract_title(self, content: str) -> str:
        """Extract a title from content."""
        # Use first line or first sentence
        lines = content.strip().split("\n")
        first_line = lines[0].strip()

        # Truncate if too long
        if len(first_line) > 100:
            return first_line[:97] + "..."

        return first_line or "Untitled Case"

    def _extract_resolution_steps(self, content: str) -> List[str]:
        """Extract resolution steps from content."""
        steps = []

        # Look for numbered lists
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            # Match patterns like "1.", "1)", "Step 1:", etc.
            if (
                line
                and (
                    line[0].isdigit()
                    or line.lower().startswith("step")
                    or line.startswith("-")
                    or line.startswith("*")
                )
            ):
                # Clean up the line
                clean_line = line.lstrip("0123456789.-)*: ")
                if clean_line and len(clean_line) > 5:
                    steps.append(clean_line)

        return steps[:10]  # Limit to 10 steps

    def filter_quality_cases(
        self,
        cases: List[Case],
        min_quality: Optional[float] = None,
    ) -> List[Case]:
        """
        Filter cases by quality score.

        Args:
            cases: List of cases to filter.
            min_quality: Minimum quality score. Uses config default if not provided.

        Returns:
            Filtered list of cases.
        """
        min_quality = min_quality or self.config.min_quality_score

        filtered = [c for c in cases if c.quality_score >= min_quality]

        logger.info(
            f"Filtered {len(cases)} cases to {len(filtered)} "
            f"(min quality: {min_quality})"
        )

        return filtered

    def filter_recent_cases(
        self,
        cases: List[Case],
        max_age_days: Optional[int] = None,
    ) -> List[Case]:
        """
        Filter cases by age.

        Args:
            cases: List of cases to filter.
            max_age_days: Maximum age in days. Uses config default if not provided.

        Returns:
            Filtered list of cases.
        """
        max_age_days = max_age_days or self.config.case_expiry_days
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        filtered = [c for c in cases if c.created_at >= cutoff]

        return filtered

    async def create_case_from_resolution(
        self,
        event_description: str,
        resolution_steps: List[str],
        outcome: CaseOutcome,
        affected_systems: List[str],
        root_cause: Optional[str] = None,
        lessons_learned: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Case:
        """
        Create a new case from a resolution for future learning.

        Args:
            event_description: Description of the event.
            resolution_steps: Steps taken to resolve.
            outcome: Outcome of the resolution.
            affected_systems: Systems affected.
            root_cause: Root cause analysis.
            lessons_learned: Lessons learned.
            user_id: User who resolved.
            tags: Tags for categorization.

        Returns:
            Created Case object.
        """
        case = Case(
            id=str(uuid4()),
            title=self._extract_title(event_description),
            description=event_description,
            category=self._infer_category(event_description, tags or []),
            outcome=outcome,
            affected_systems=affected_systems,
            root_cause=root_cause,
            resolution_steps=resolution_steps,
            lessons_learned=lessons_learned,
            quality_score=0.7 if outcome == CaseOutcome.SUCCESS else 0.4,
            metadata=CaseMetadata(
                source="manual",
                tags=tags or [],
                custom={
                    "root_cause": root_cause,
                    "lessons_learned": lessons_learned,
                },
            ),
            created_at=datetime.utcnow(),
        )

        # Store in memory if available
        if self._memory_manager:
            try:
                from src.integrations.memory import MemoryType, MemoryMetadata

                await self._memory_manager.add(
                    content=event_description,
                    user_id=user_id or "system",
                    memory_type=MemoryType.EVENT_RESOLUTION,
                    metadata=MemoryMetadata(
                        source="case_extractor",
                        importance=case.quality_score,
                        tags=tags or [],
                        custom={
                            "case_id": case.id,
                            "resolution_steps": resolution_steps,
                            "root_cause": root_cause,
                            "affected_systems": affected_systems,
                        },
                    ),
                )
                logger.info(f"Case {case.id} stored in memory")

            except Exception as e:
                logger.warning(f"Failed to store case in memory: {e}")

        # Cache the case
        self._case_cache[case.id] = case

        return case

    def get_cached_case(self, case_id: str) -> Optional[Case]:
        """Get a case from cache by ID."""
        return self._case_cache.get(case_id)

    def clear_cache(self) -> None:
        """Clear the case cache."""
        self._case_cache.clear()
        logger.info("Case cache cleared")
