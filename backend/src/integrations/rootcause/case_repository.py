"""
Case Repository — 歷史案例儲存庫

Sprint 130 — Story 130-2: RootCause 真實案例庫

提供:
- CaseRepository: 歷史案例 CRUD + 查詢
- 15 個種子案例（IT Ops 真實場景）
- ServiceNow 匯入支援

設計:
- 介面相容 PostgreSQL (SQLAlchemy) 和 in-memory 模式
- In-memory 模式用於測試和未部署資料庫時的 fallback
- Seed cases 自動載入
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .types import HistoricalCase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed Data — 15 IT Ops Historical Cases
# ---------------------------------------------------------------------------

_SEED_CASES: List[Dict[str, Any]] = [
    {
        "case_id": "HC-001",
        "title": "Database Connection Pool Exhaustion",
        "description": "Production database connection pool reached 100% capacity "
        "during peak traffic, causing cascading request timeouts across API services.",
        "root_cause": "Connection pool size (max_connections=20) insufficient for "
        "traffic spike; leaked connections from failed transactions not properly released.",
        "resolution": "Increased pool size to 50, added connection timeout policy (30s), "
        "implemented connection leak detection with automatic eviction.",
        "category": "database",
        "severity": "critical",
        "lessons_learned": [
            "Monitor connection pool utilization with alerts at 80%",
            "Set connection timeout and idle eviction policies",
            "Load test connection pool under peak traffic scenarios",
        ],
    },
    {
        "case_id": "HC-002",
        "title": "Memory Leak in Node.js API Service",
        "description": "Gradual memory increase over 72 hours leading to OOM kill "
        "of API pod; heap grew from 512MB to 4GB before restart.",
        "root_cause": "Event listeners attached in request handler but never removed; "
        "each request added a new listener, preventing garbage collection.",
        "resolution": "Fixed event listener cleanup in request lifecycle, added "
        "process.memoryUsage() monitoring, set memory limits with restart policy.",
        "category": "application",
        "severity": "error",
        "lessons_learned": [
            "Implement memory profiling in staging environment",
            "Set Kubernetes memory limits with graceful restart",
            "Monitor heap size trends (not just current usage)",
        ],
    },
    {
        "case_id": "HC-003",
        "title": "DNS Resolution Failure",
        "description": "Intermittent DNS resolution failures for internal services "
        "causing 5xx errors on 15% of requests during 2-hour window.",
        "root_cause": "CoreDNS pod resource limits too low, causing OOMKill under "
        "load; DNS cache TTL set to 0 causing excessive lookups.",
        "resolution": "Increased CoreDNS resource limits, set DNS cache TTL to 30s, "
        "added ndots:2 to pod DNS config to reduce search domain attempts.",
        "category": "network",
        "severity": "error",
        "lessons_learned": [
            "Monitor DNS resolution latency and failure rates",
            "Tune CoreDNS resource limits based on cluster size",
            "Use appropriate ndots setting to reduce DNS query volume",
        ],
    },
    {
        "case_id": "HC-004",
        "title": "Redis Cluster Split-Brain",
        "description": "Redis Sentinel promoted new master while old master was still "
        "accepting writes, causing data inconsistency across 3 services.",
        "root_cause": "Network partition between Sentinel quorum and Redis master "
        "node; down-after-milliseconds set too low (5s) causing false failover.",
        "resolution": "Adjusted Sentinel timing (down-after: 30s, failover-timeout: 180s), "
        "enabled min-replicas-to-write=1 on master, added network monitoring.",
        "category": "infrastructure",
        "severity": "critical",
        "lessons_learned": [
            "Test Sentinel failover scenarios regularly",
            "Set conservative Sentinel timing to avoid false failovers",
            "Enable min-replicas-to-write to prevent split-brain writes",
        ],
    },
    {
        "case_id": "HC-005",
        "title": "Certificate Expiry Causing TLS Handshake Failures",
        "description": "Internal service-to-service TLS certificates expired, "
        "blocking all inter-service communication for 45 minutes.",
        "root_cause": "Certificate rotation automation failed silently 2 weeks prior; "
        "no monitoring on certificate expiry dates.",
        "resolution": "Renewed certificates, fixed cert-manager CRD configuration, "
        "added certificate expiry monitoring with 30-day alerting.",
        "category": "security",
        "severity": "critical",
        "lessons_learned": [
            "Monitor certificate expiry with 30-day and 7-day alerts",
            "Test certificate rotation automation monthly",
            "Maintain certificate inventory with expiry tracking",
        ],
    },
    {
        "case_id": "HC-006",
        "title": "ETL Pipeline Data Skew",
        "description": "Daily ETL pipeline running 8x slower than normal due to "
        "data skew in partition key, causing downstream report delays.",
        "root_cause": "New customer onboarded with 10M records on single partition key; "
        "Spark shuffle stage bottlenecked on one executor.",
        "resolution": "Added salted partition key for large accounts, configured "
        "adaptive query execution (AQE), set partition size target to 128MB.",
        "category": "data",
        "severity": "warning",
        "lessons_learned": [
            "Monitor partition sizes and skew metrics",
            "Enable adaptive query execution for Spark workloads",
            "Design partition keys with growth patterns in mind",
        ],
    },
    {
        "case_id": "HC-007",
        "title": "Kubernetes Node NotReady Due to Disk Pressure",
        "description": "3 of 8 worker nodes entered NotReady state due to disk "
        "pressure, causing pod evictions and service degradation.",
        "root_cause": "Container image layer cache and unused images consumed 90% "
        "of node disk; garbage collection thresholds not configured.",
        "resolution": "Configured kubelet image GC thresholds (highThreshold: 85%, "
        "lowThreshold: 80%), added disk usage monitoring, pruned unused images.",
        "category": "infrastructure",
        "severity": "error",
        "lessons_learned": [
            "Configure kubelet garbage collection thresholds",
            "Monitor node disk usage with predictive alerts",
            "Schedule regular image pruning jobs",
        ],
    },
    {
        "case_id": "HC-008",
        "title": "API Rate Limiting Misconfiguration",
        "description": "Rate limiter blocked legitimate traffic after deployment "
        "reset the rate counter; 30% of users affected for 20 minutes.",
        "root_cause": "Rate limit configuration stored in ConfigMap was overwritten "
        "during Helm chart upgrade; limits dropped from 1000/min to 10/min.",
        "resolution": "Moved rate limit config to dedicated values file, added "
        "validation webhook for ConfigMap changes, rollback procedure documented.",
        "category": "application",
        "severity": "warning",
        "lessons_learned": [
            "Validate configuration changes in CI pipeline",
            "Use immutable ConfigMaps with versioned names",
            "Test rate limiter behavior as part of deployment smoke tests",
        ],
    },
    {
        "case_id": "HC-009",
        "title": "Message Queue Consumer Lag",
        "description": "RabbitMQ consumer lag grew to 500K messages over 4 hours, "
        "causing order processing delays of 2+ hours.",
        "root_cause": "Consumer prefetch count set to 1 with acknowledge-after-processing; "
        "slow downstream API (3s avg) limited throughput to 20 msg/min per consumer.",
        "resolution": "Increased prefetch to 10, added consumer auto-scaling based on "
        "queue depth, optimized downstream API call batching.",
        "category": "messaging",
        "severity": "error",
        "lessons_learned": [
            "Monitor consumer lag with alerting thresholds",
            "Tune prefetch count based on processing time",
            "Implement auto-scaling consumers for variable workloads",
        ],
    },
    {
        "case_id": "HC-010",
        "title": "Deployment Rollback Due to Schema Migration",
        "description": "Production deployment required rollback after database "
        "migration dropped column still referenced by running pods.",
        "root_cause": "Schema migration and application deployment not coordinated; "
        "column drop executed before all old pods terminated.",
        "resolution": "Implemented expand-contract migration pattern: Phase 1 adds "
        "new column, Phase 2 deploys new code, Phase 3 drops old column.",
        "category": "deployment",
        "severity": "critical",
        "lessons_learned": [
            "Use expand-contract pattern for breaking schema changes",
            "Never drop columns in same deployment as code change",
            "Run migration dry-run in staging with production-like traffic",
        ],
    },
    {
        "case_id": "HC-011",
        "title": "Authentication Service Token Validation Failure",
        "description": "JWT token validation failures across all services after "
        "key rotation; 100% auth failure rate for 10 minutes.",
        "root_cause": "Key rotation script updated issuer key but not the JWKS "
        "endpoint cache; services cached old JWKS for 1 hour.",
        "resolution": "Fixed JWKS cache invalidation on key rotation, reduced "
        "JWKS cache TTL to 5 minutes, added dual-key support during rotation.",
        "category": "security",
        "severity": "critical",
        "lessons_learned": [
            "Support multiple active signing keys during rotation",
            "Reduce JWKS cache TTL and add cache invalidation mechanism",
            "Test key rotation in staging with full service mesh",
        ],
    },
    {
        "case_id": "HC-012",
        "title": "Log Volume Spike Exhausting Storage",
        "description": "Debug logging accidentally enabled in production caused "
        "10x log volume increase, filling Elasticsearch storage in 6 hours.",
        "root_cause": "Feature flag for debug logging had no environment guard; "
        "developer enabled it for testing and merged to production branch.",
        "resolution": "Added environment-aware log level configuration, implemented "
        "log sampling for high-volume paths, added storage capacity alerts.",
        "category": "observability",
        "severity": "warning",
        "lessons_learned": [
            "Log level changes require production approval",
            "Implement log sampling for high-throughput services",
            "Monitor log ingestion rate with automatic throttling",
        ],
    },
    {
        "case_id": "HC-013",
        "title": "Cascading Timeout in Microservice Chain",
        "description": "Timeout in service-D propagated upstream through service-C, "
        "B, and A, causing 100% failure rate on the entire order flow.",
        "root_cause": "All services used default 30s timeout; when service-D slowed "
        "to 25s response time, upstream services timed out sequentially.",
        "resolution": "Implemented timeout budget pattern (decreasing timeouts per hop), "
        "added circuit breakers at each service boundary, set per-route timeouts.",
        "category": "network",
        "severity": "critical",
        "lessons_learned": [
            "Implement timeout budgets that decrease per hop",
            "Add circuit breakers at every service boundary",
            "Set per-endpoint timeouts based on expected latency",
        ],
    },
    {
        "case_id": "HC-014",
        "title": "Cron Job Overlap Causing Deadlocks",
        "description": "Scheduled batch job ran longer than interval, causing "
        "concurrent instances to deadlock on shared database resources.",
        "root_cause": "Cron job interval (5 min) shorter than execution time (8 min); "
        "no distributed lock preventing concurrent execution.",
        "resolution": "Added distributed lock (Redis SETNX) for job execution, "
        "increased interval to 15 min, added job duration monitoring.",
        "category": "application",
        "severity": "error",
        "lessons_learned": [
            "Use distributed locks for singleton scheduled jobs",
            "Monitor job duration vs schedule interval",
            "Implement job overlap detection with alerting",
        ],
    },
    {
        "case_id": "HC-015",
        "title": "CDN Cache Poisoning After Config Change",
        "description": "CDN served stale API responses for 2 hours after backend "
        "API version upgrade due to aggressive cache-control headers.",
        "root_cause": "API response Cache-Control header set to max-age=86400 for "
        "static assets also applied to dynamic API responses.",
        "resolution": "Separated cache-control policies for static and dynamic "
        "content, added cache purge to deployment pipeline, implemented "
        "versioned API endpoints.",
        "category": "infrastructure",
        "severity": "warning",
        "lessons_learned": [
            "Separate cache policies for static vs dynamic content",
            "Include cache purge in deployment automation",
            "Use versioned URLs for cache-busting on deploys",
        ],
    },
]


# ---------------------------------------------------------------------------
# CaseRepository
# ---------------------------------------------------------------------------


class CaseRepository:
    """
    歷史案例儲存庫

    提供案例的 CRUD 操作、搜索和統計功能。
    支援 in-memory 模式（自動載入 seed data）和 PostgreSQL 模式。
    """

    def __init__(
        self,
        db_session: Optional[Any] = None,
        seed: bool = True,
    ):
        """
        Initialize case repository.

        Args:
            db_session: Optional SQLAlchemy async session. If None, uses in-memory store.
            seed: Whether to load seed cases on init (in-memory mode only).
        """
        self._session = db_session
        self._cases: Dict[str, HistoricalCase] = {}

        if db_session is None and seed:
            self._load_seed_cases()

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def get_case(self, case_id: str) -> Optional[HistoricalCase]:
        """
        Get a single case by ID.

        Args:
            case_id: The case identifier.

        Returns:
            HistoricalCase or None.
        """
        return self._cases.get(case_id)

    async def create_case(self, case: HistoricalCase) -> HistoricalCase:
        """
        Create a new case.

        Args:
            case: HistoricalCase to store.

        Returns:
            The stored case.
        """
        if case.case_id in self._cases:
            raise ValueError(f"Case {case.case_id} already exists")
        self._cases[case.case_id] = case
        logger.info(f"Created case: {case.case_id} — {case.title}")
        return case

    async def update_case(
        self,
        case_id: str,
        updates: Dict[str, Any],
    ) -> Optional[HistoricalCase]:
        """
        Update an existing case.

        Args:
            case_id: The case to update.
            updates: Dict of field -> new_value.

        Returns:
            Updated HistoricalCase or None if not found.
        """
        existing = self._cases.get(case_id)
        if not existing:
            return None

        # Build updated case (immutability: create new instance)
        case_dict = {
            "case_id": existing.case_id,
            "title": existing.title,
            "description": existing.description,
            "root_cause": existing.root_cause,
            "resolution": existing.resolution,
            "occurred_at": existing.occurred_at,
            "resolved_at": existing.resolved_at,
            "similarity_score": existing.similarity_score,
            "lessons_learned": list(existing.lessons_learned),
        }
        case_dict.update(updates)

        updated = HistoricalCase(**case_dict)
        self._cases[case_id] = updated
        logger.info(f"Updated case: {case_id}")
        return updated

    async def delete_case(self, case_id: str) -> bool:
        """
        Delete a case.

        Args:
            case_id: The case to delete.

        Returns:
            True if deleted, False if not found.
        """
        if case_id in self._cases:
            del self._cases[case_id]
            logger.info(f"Deleted case: {case_id}")
            return True
        return False

    # ------------------------------------------------------------------
    # Search & Query
    # ------------------------------------------------------------------

    async def search_cases(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
    ) -> List[HistoricalCase]:
        """
        Search cases by text, category, and/or severity.

        Args:
            query: Optional text search (matches title, description, root_cause).
            category: Optional category filter.
            severity: Optional severity filter.
            limit: Maximum results.

        Returns:
            List of matching HistoricalCase objects.
        """
        results: List[HistoricalCase] = []

        for case in self._cases.values():
            # Category filter (stored in case metadata or inferred from seed)
            if category:
                case_cat = self._get_case_category(case)
                if case_cat and case_cat.lower() != category.lower():
                    continue

            # Severity filter
            if severity:
                case_sev = self._get_case_severity(case)
                if case_sev and case_sev.lower() != severity.lower():
                    continue

            # Text search
            if query:
                search_text = (
                    f"{case.title} {case.description} {case.root_cause}"
                ).lower()
                if query.lower() not in search_text:
                    continue

            results.append(case)

        return results[:limit]

    async def get_all_cases(self) -> List[HistoricalCase]:
        """Get all stored cases."""
        return list(self._cases.values())

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get repository statistics.

        Returns:
            Statistics dict with total, categories, severities, etc.
        """
        categories: Dict[str, int] = {}
        severities: Dict[str, int] = {}

        for case in self._cases.values():
            cat = self._get_case_category(case) or "unknown"
            categories[cat] = categories.get(cat, 0) + 1

            sev = self._get_case_severity(case) or "unknown"
            severities[sev] = severities.get(sev, 0) + 1

        return {
            "total_cases": len(self._cases),
            "categories": categories,
            "severities": severities,
            "case_ids": list(self._cases.keys()),
        }

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    async def import_from_servicenow(
        self,
        incidents: List[Dict[str, Any]],
    ) -> int:
        """
        Import historical cases from ServiceNow closed incidents.

        Expected incident dict format:
        {
            "number": "INC0012345",
            "short_description": "...",
            "description": "...",
            "close_notes": "...",  (-> root_cause + resolution)
            "resolved_at": "2025-01-15T10:00:00Z",
            "opened_at": "2025-01-14T08:00:00Z",
            "category": "...",
            "priority": "1-5",
        }

        Args:
            incidents: List of ServiceNow incident dicts.

        Returns:
            Number of cases imported.
        """
        imported = 0
        for inc in incidents:
            case_id = inc.get("number", f"SN-{uuid4().hex[:8]}")

            if case_id in self._cases:
                continue

            close_notes = inc.get("close_notes", "")
            root_cause = close_notes.split("Resolution:")
            rc_text = root_cause[0].strip() if root_cause else close_notes
            resolution = root_cause[1].strip() if len(root_cause) > 1 else close_notes

            # Parse timestamps
            opened_at = _parse_datetime(inc.get("opened_at"))
            resolved_at = _parse_datetime(inc.get("resolved_at"))

            case = HistoricalCase(
                case_id=case_id,
                title=inc.get("short_description", "Imported incident"),
                description=inc.get("description", ""),
                root_cause=rc_text,
                resolution=resolution,
                occurred_at=opened_at or datetime.utcnow(),
                resolved_at=resolved_at,
                similarity_score=0.0,
                lessons_learned=_extract_lessons(close_notes),
            )

            self._cases[case_id] = case
            imported += 1

        logger.info(f"Imported {imported} cases from ServiceNow")
        return imported

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    def _load_seed_cases(self) -> None:
        """Load the 15 seed cases into the in-memory store."""
        base_time = datetime.utcnow() - timedelta(days=180)

        for i, data in enumerate(_SEED_CASES):
            occurred_at = base_time - timedelta(days=(15 - i) * 10)
            resolved_at = occurred_at + timedelta(hours=2 + i)

            case = HistoricalCase(
                case_id=data["case_id"],
                title=data["title"],
                description=data["description"],
                root_cause=data["root_cause"],
                resolution=data["resolution"],
                occurred_at=occurred_at,
                resolved_at=resolved_at,
                similarity_score=0.0,
                lessons_learned=data["lessons_learned"],
            )
            self._cases[case.case_id] = case

        logger.debug(f"Loaded {len(self._cases)} seed cases")

    def _get_case_category(self, case: HistoricalCase) -> Optional[str]:
        """Extract category from seed data metadata or title heuristics."""
        for seed in _SEED_CASES:
            if seed["case_id"] == case.case_id:
                return seed.get("category")

        # Heuristic fallback
        title_lower = case.title.lower()
        if "database" in title_lower or "sql" in title_lower:
            return "database"
        if "network" in title_lower or "dns" in title_lower or "timeout" in title_lower:
            return "network"
        if "memory" in title_lower or "cpu" in title_lower:
            return "application"
        if "certificate" in title_lower or "auth" in title_lower or "token" in title_lower:
            return "security"
        if "deploy" in title_lower or "rollback" in title_lower:
            return "deployment"
        return None

    def _get_case_severity(self, case: HistoricalCase) -> Optional[str]:
        """Extract severity from seed data metadata."""
        for seed in _SEED_CASES:
            if seed["case_id"] == case.case_id:
                return seed.get("severity")
        return None


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse a datetime string, returning None on failure."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
        except ValueError:
            return None
    return None


def _extract_lessons(close_notes: str) -> List[str]:
    """Extract lessons learned from ServiceNow close notes."""
    if not close_notes:
        return []

    lessons = []
    for line in close_notes.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            lessons.append(line[2:].strip())
        elif line.startswith("Lesson:") or line.startswith("Learning:"):
            lessons.append(line.split(":", 1)[1].strip())

    return lessons if lessons else ["Review close notes for detailed findings"]
