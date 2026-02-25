"""Unit tests for CaseRepository — historical case CRUD and seed data.

Tests cover:
    - Seed data loading (15 cases)
    - CRUD operations (create, get, update, delete)
    - Search by text, category, severity
    - Statistics calculation
    - ServiceNow import
    - Error handling (duplicate create)

Sprint 130 — Story 130-3
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.integrations.rootcause.case_repository import (
    CaseRepository,
    _SEED_CASES,
    _extract_lessons,
    _parse_datetime,
)
from src.integrations.rootcause.types import HistoricalCase


# ---------------------------------------------------------------------------
# Seed Data
# ---------------------------------------------------------------------------


class TestSeedData:
    """Tests for seed data loading."""

    def test_seed_cases_count(self) -> None:
        """Repository loads 15 seed cases."""
        repo = CaseRepository()
        assert len(repo._cases) == 15

    def test_seed_cases_have_required_fields(self) -> None:
        """All seed cases have required fields populated."""
        repo = CaseRepository()
        for case_id, case in repo._cases.items():
            assert case.case_id, f"Missing case_id on {case_id}"
            assert case.title, f"Missing title on {case_id}"
            assert case.description, f"Missing description on {case_id}"
            assert case.root_cause, f"Missing root_cause on {case_id}"
            assert case.resolution, f"Missing resolution on {case_id}"
            assert case.occurred_at is not None, f"Missing occurred_at on {case_id}"
            assert len(case.lessons_learned) > 0, f"No lessons_learned on {case_id}"

    def test_seed_case_ids_sequential(self) -> None:
        """Seed cases have IDs HC-001 through HC-015."""
        repo = CaseRepository()
        for i in range(1, 16):
            case_id = f"HC-{i:03d}"
            assert case_id in repo._cases, f"Missing seed case {case_id}"

    def test_no_seed_when_disabled(self) -> None:
        """Repository loads no seed data when seed=False."""
        repo = CaseRepository(seed=False)
        assert len(repo._cases) == 0

    def test_seed_data_definition_count(self) -> None:
        """_SEED_CASES has exactly 15 entries."""
        assert len(_SEED_CASES) == 15


# ---------------------------------------------------------------------------
# CRUD — Get
# ---------------------------------------------------------------------------


class TestCaseRepositoryGet:
    """Tests for get operations."""

    @pytest.mark.asyncio
    async def test_get_existing_case(self) -> None:
        """get_case returns case for valid ID."""
        repo = CaseRepository()
        case = await repo.get_case("HC-001")

        assert case is not None
        assert case.case_id == "HC-001"
        assert "Database Connection Pool" in case.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_case(self) -> None:
        """get_case returns None for unknown ID."""
        repo = CaseRepository()
        case = await repo.get_case("NONEXISTENT")

        assert case is None

    @pytest.mark.asyncio
    async def test_get_all_cases(self) -> None:
        """get_all_cases returns all stored cases."""
        repo = CaseRepository()
        all_cases = await repo.get_all_cases()

        assert len(all_cases) == 15


# ---------------------------------------------------------------------------
# CRUD — Create
# ---------------------------------------------------------------------------


class TestCaseRepositoryCreate:
    """Tests for create operations."""

    @pytest.mark.asyncio
    async def test_create_case_success(self) -> None:
        """create_case stores and returns new case."""
        repo = CaseRepository(seed=False)
        case = HistoricalCase(
            case_id="NEW-001",
            title="New Test Case",
            description="Test description",
            root_cause="Test root cause",
            resolution="Test resolution",
            occurred_at=datetime.utcnow(),
            resolved_at=datetime.utcnow(),
            similarity_score=0.0,
            lessons_learned=["Lesson 1"],
        )

        result = await repo.create_case(case)
        assert result.case_id == "NEW-001"

        # Verify stored
        stored = await repo.get_case("NEW-001")
        assert stored is not None
        assert stored.title == "New Test Case"

    @pytest.mark.asyncio
    async def test_create_duplicate_raises(self) -> None:
        """create_case raises ValueError for duplicate ID."""
        repo = CaseRepository()

        duplicate = HistoricalCase(
            case_id="HC-001",  # already exists
            title="Duplicate",
            description="",
            root_cause="",
            resolution="",
            occurred_at=datetime.utcnow(),
            resolved_at=None,
            similarity_score=0.0,
        )

        with pytest.raises(ValueError, match="already exists"):
            await repo.create_case(duplicate)


# ---------------------------------------------------------------------------
# CRUD — Update
# ---------------------------------------------------------------------------


class TestCaseRepositoryUpdate:
    """Tests for update operations."""

    @pytest.mark.asyncio
    async def test_update_case_success(self) -> None:
        """update_case modifies fields and returns updated case."""
        repo = CaseRepository()

        updated = await repo.update_case("HC-001", {"title": "Updated Title"})

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.case_id == "HC-001"

        # Verify stored
        stored = await repo.get_case("HC-001")
        assert stored.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self) -> None:
        """update_case returns None for unknown ID."""
        repo = CaseRepository()
        result = await repo.update_case("NONEXISTENT", {"title": "X"})

        assert result is None


# ---------------------------------------------------------------------------
# CRUD — Delete
# ---------------------------------------------------------------------------


class TestCaseRepositoryDelete:
    """Tests for delete operations."""

    @pytest.mark.asyncio
    async def test_delete_case_success(self) -> None:
        """delete_case removes case and returns True."""
        repo = CaseRepository()

        result = await repo.delete_case("HC-001")
        assert result is True

        # Verify deleted
        case = await repo.get_case("HC-001")
        assert case is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self) -> None:
        """delete_case returns False for unknown ID."""
        repo = CaseRepository()
        result = await repo.delete_case("NONEXISTENT")

        assert result is False


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestCaseRepositorySearch:
    """Tests for search and query operations."""

    @pytest.mark.asyncio
    async def test_search_by_text(self) -> None:
        """search_cases finds cases matching text query."""
        repo = CaseRepository()
        results = await repo.search_cases(query="database")

        assert len(results) > 0
        assert any("Database" in c.title or "database" in c.description.lower()
                    for c in results)

    @pytest.mark.asyncio
    async def test_search_by_category(self) -> None:
        """search_cases filters by category."""
        repo = CaseRepository()
        results = await repo.search_cases(category="security")

        assert len(results) > 0
        # HC-005 (Certificate) and HC-011 (Auth) are security
        case_ids = [c.case_id for c in results]
        assert "HC-005" in case_ids or "HC-011" in case_ids

    @pytest.mark.asyncio
    async def test_search_by_severity(self) -> None:
        """search_cases filters by severity."""
        repo = CaseRepository()
        results = await repo.search_cases(severity="critical")

        assert len(results) > 0
        # HC-001, HC-004, HC-005, HC-010, HC-011, HC-013 are critical
        assert len(results) >= 5

    @pytest.mark.asyncio
    async def test_search_combined_filters(self) -> None:
        """search_cases combines text + category + severity."""
        repo = CaseRepository()
        results = await repo.search_cases(
            query="connection",
            category="database",
            severity="critical",
        )

        assert len(results) >= 1
        assert results[0].case_id == "HC-001"

    @pytest.mark.asyncio
    async def test_search_no_results(self) -> None:
        """search_cases returns empty for non-matching query."""
        repo = CaseRepository()
        results = await repo.search_cases(query="zzz_nonexistent_zzz")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_limit(self) -> None:
        """search_cases respects limit parameter."""
        repo = CaseRepository()
        results = await repo.search_cases(limit=3)

        assert len(results) <= 3


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestCaseRepositoryStatistics:
    """Tests for statistics."""

    @pytest.mark.asyncio
    async def test_statistics_total(self) -> None:
        """Statistics shows correct total count."""
        repo = CaseRepository()
        stats = await repo.get_statistics()

        assert stats["total_cases"] == 15

    @pytest.mark.asyncio
    async def test_statistics_categories(self) -> None:
        """Statistics includes category distribution."""
        repo = CaseRepository()
        stats = await repo.get_statistics()

        cats = stats["categories"]
        assert "database" in cats
        assert "network" in cats
        assert "security" in cats

    @pytest.mark.asyncio
    async def test_statistics_severities(self) -> None:
        """Statistics includes severity distribution."""
        repo = CaseRepository()
        stats = await repo.get_statistics()

        sevs = stats["severities"]
        assert "critical" in sevs
        assert "error" in sevs
        assert "warning" in sevs


# ---------------------------------------------------------------------------
# ServiceNow Import
# ---------------------------------------------------------------------------


class TestCaseRepositoryImport:
    """Tests for ServiceNow import."""

    @pytest.mark.asyncio
    async def test_import_basic(self) -> None:
        """import_from_servicenow creates cases from incidents."""
        repo = CaseRepository(seed=False)

        incidents = [
            {
                "number": "INC001",
                "short_description": "Server down",
                "description": "Production server unresponsive",
                "close_notes": "Root cause: disk full. Resolution: cleaned logs",
                "opened_at": "2026-01-15T08:00:00Z",
                "resolved_at": "2026-01-15T10:00:00Z",
            },
            {
                "number": "INC002",
                "short_description": "Login failures",
                "description": "Users unable to login",
                "close_notes": "Expired certificate",
                "opened_at": "2026-01-20T12:00:00Z",
            },
        ]

        count = await repo.import_from_servicenow(incidents)
        assert count == 2

        case1 = await repo.get_case("INC001")
        assert case1 is not None
        assert case1.title == "Server down"

    @pytest.mark.asyncio
    async def test_import_skips_duplicates(self) -> None:
        """import_from_servicenow skips existing case IDs."""
        repo = CaseRepository(seed=False)

        # First import
        incidents = [{"number": "INC001", "short_description": "Test"}]
        count1 = await repo.import_from_servicenow(incidents)
        assert count1 == 1

        # Second import (same ID)
        count2 = await repo.import_from_servicenow(incidents)
        assert count2 == 0


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Tests for repository helper functions."""

    def test_parse_datetime_iso(self) -> None:
        """Parses ISO 8601 datetime string."""
        result = _parse_datetime("2026-02-25T10:00:00Z")
        assert isinstance(result, datetime)

    def test_parse_datetime_invalid(self) -> None:
        """Returns None for invalid datetime string."""
        assert _parse_datetime("not-a-date") is None

    def test_parse_datetime_none(self) -> None:
        """Returns None for None input."""
        assert _parse_datetime(None) is None

    def test_extract_lessons_bullet_points(self) -> None:
        """Extracts lessons from bullet-pointed text."""
        text = "Summary\n- Lesson one\n- Lesson two\nEnd"
        lessons = _extract_lessons(text)
        assert len(lessons) == 2
        assert "Lesson one" in lessons

    def test_extract_lessons_empty(self) -> None:
        """Returns empty list for empty text."""
        assert _extract_lessons("") == []
