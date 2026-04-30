# =============================================================================
# IPA Platform - Learning Service Unit Tests
# =============================================================================
# Sprint 4: Developer Experience - Few-shot Learning Mechanism
#
# Comprehensive tests for learning case management:
#   - Case creation and management
#   - Approval workflow
#   - Similarity search
#   - Few-shot prompt building
#   - Effectiveness tracking
#   - API endpoints
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.domain.learning import (
    CaseStatus,
    LearningCase,
    LearningService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def learning_service():
    """Create a learning service instance."""
    return LearningService(
        similarity_threshold=0.5,
        max_examples=5,
    )


@pytest.fixture
def sample_case(learning_service):
    """Create a sample learning case."""
    return learning_service.record_correction(
        scenario="it_triage",
        original_input="My computer is slow",
        original_output='{"type": "hardware", "priority": "P4"}',
        corrected_output='{"type": "software", "priority": "P3"}',
        feedback="Software issue, not hardware. Medium priority due to productivity impact.",
        tags=["performance", "software"],
    )


@pytest.fixture
def approved_case(learning_service, sample_case):
    """Create an approved learning case."""
    learning_service.approve_case(sample_case.id, "admin")
    return sample_case


# =============================================================================
# LearningCase Tests
# =============================================================================


class TestLearningCase:
    """Tests for LearningCase class."""

    def test_create_case(self, sample_case):
        """Test case creation."""
        assert sample_case.id is not None
        assert sample_case.scenario == "it_triage"
        assert sample_case.status == CaseStatus.PENDING
        assert len(sample_case.tags) == 2

    def test_approve_case(self, sample_case):
        """Test case approval."""
        sample_case.approve("admin")
        assert sample_case.status == CaseStatus.APPROVED
        assert sample_case.approved_at is not None
        assert sample_case.approved_by == "admin"

    def test_reject_case(self, sample_case):
        """Test case rejection."""
        sample_case.reject("Not a valid correction")
        assert sample_case.status == CaseStatus.REJECTED
        assert sample_case.rejection_reason == "Not a valid correction"

    def test_archive_case(self, sample_case):
        """Test case archiving."""
        sample_case.archive()
        assert sample_case.status == CaseStatus.ARCHIVED

    def test_increment_usage(self, sample_case):
        """Test usage counter."""
        initial = sample_case.usage_count
        sample_case.increment_usage()
        assert sample_case.usage_count == initial + 1

    def test_case_to_dict(self, sample_case):
        """Test case serialization."""
        data = sample_case.to_dict()
        assert data["scenario"] == "it_triage"
        assert data["status"] == "pending"
        assert "created_at" in data


# =============================================================================
# LearningService Tests
# =============================================================================


class TestLearningService:
    """Tests for LearningService class."""

    def test_record_correction(self, learning_service):
        """Test recording a correction."""
        case = learning_service.record_correction(
            scenario="customer_service",
            original_input="I want a refund",
            original_output="Please contact support",
            corrected_output="I'll process your refund immediately",
            feedback="Should be more helpful and direct",
        )
        assert case is not None
        assert case.scenario == "customer_service"

    def test_get_case(self, learning_service, sample_case):
        """Test getting case by ID."""
        retrieved = learning_service.get_case(sample_case.id)
        assert retrieved is not None
        assert retrieved.id == sample_case.id

    def test_get_case_not_found(self, learning_service):
        """Test getting non-existent case."""
        result = learning_service.get_case(uuid4())
        assert result is None

    def test_list_cases(self, learning_service, sample_case):
        """Test listing cases."""
        cases = learning_service.list_cases()
        assert len(cases) >= 1
        assert sample_case.id in [c.id for c in cases]

    def test_list_cases_by_scenario(self, learning_service, sample_case):
        """Test filtering by scenario."""
        # Add another case with different scenario
        learning_service.record_correction(
            scenario="customer_service",
            original_input="test",
            original_output="test",
            corrected_output="test",
            feedback="test",
        )

        cases = learning_service.list_cases(scenario="it_triage")
        assert all(c.scenario == "it_triage" for c in cases)

    def test_list_cases_by_status(self, learning_service, sample_case):
        """Test filtering by status."""
        learning_service.approve_case(sample_case.id)

        cases = learning_service.list_cases(status=CaseStatus.APPROVED)
        assert all(c.status == CaseStatus.APPROVED for c in cases)

    def test_list_cases_by_tags(self, learning_service, sample_case):
        """Test filtering by tags."""
        cases = learning_service.list_cases(tags=["performance"])
        assert len(cases) >= 1

    def test_delete_case(self, learning_service, sample_case):
        """Test deleting a case."""
        case_id = sample_case.id
        assert learning_service.delete_case(case_id) is True
        assert learning_service.get_case(case_id) is None

    def test_delete_case_not_found(self, learning_service):
        """Test deleting non-existent case."""
        assert learning_service.delete_case(uuid4()) is False

    # Approval tests
    def test_approve_case(self, learning_service, sample_case):
        """Test approving a case."""
        case = learning_service.approve_case(sample_case.id, "admin")
        assert case is not None
        assert case.status == CaseStatus.APPROVED

    def test_approve_case_not_found(self, learning_service):
        """Test approving non-existent case."""
        result = learning_service.approve_case(uuid4())
        assert result is None

    def test_reject_case(self, learning_service, sample_case):
        """Test rejecting a case."""
        case = learning_service.reject_case(sample_case.id, "Not relevant")
        assert case is not None
        assert case.status == CaseStatus.REJECTED

    def test_bulk_approve(self, learning_service):
        """Test bulk approval."""
        # Create multiple cases
        cases = []
        for i in range(3):
            case = learning_service.record_correction(
                scenario="test",
                original_input=f"input {i}",
                original_output=f"output {i}",
                corrected_output=f"corrected {i}",
                feedback=f"feedback {i}",
            )
            cases.append(case)

        case_ids = [c.id for c in cases]
        approved = learning_service.bulk_approve(case_ids, "admin")
        assert approved == 3

    # Similarity search tests
    def test_get_similar_cases(self, learning_service, approved_case):
        """Test finding similar cases."""
        similar = learning_service.get_similar_cases(
            scenario="it_triage",
            input_text="My laptop is running slowly",
        )
        assert len(similar) >= 1
        assert similar[0]["similarity"] > 0.5

    def test_get_similar_cases_no_match(self, learning_service, approved_case):
        """Test with no similar cases."""
        similar = learning_service.get_similar_cases(
            scenario="it_triage",
            input_text="xyz completely unrelated text 12345",
        )
        # May or may not find matches depending on threshold
        assert isinstance(similar, list)

    def test_get_similar_cases_approved_only(self, learning_service, sample_case):
        """Test that unapproved cases are excluded by default."""
        similar = learning_service.get_similar_cases(
            scenario="it_triage",
            input_text="My computer is slow",
            approved_only=True,
        )
        # Sample case is not approved
        assert all(s["case"].status == CaseStatus.APPROVED for s in similar)

    # Few-shot prompt tests
    def test_build_few_shot_prompt(self, learning_service, approved_case):
        """Test building few-shot prompt."""
        prompt = learning_service.build_few_shot_prompt(
            base_prompt="You are an IT support agent.",
            scenario="it_triage",
            input_text="My computer is slow",
        )
        assert "Learning Examples" in prompt
        assert "My computer is slow" in prompt

    def test_build_few_shot_prompt_no_examples(self, learning_service):
        """Test prompt with no examples."""
        prompt = learning_service.build_few_shot_prompt(
            base_prompt="Base prompt",
            scenario="nonexistent_scenario",
            input_text="test input",
        )
        # Should return base prompt unchanged
        assert prompt == "Base prompt"

    def test_build_few_shot_prompt_chat_format(self, learning_service, approved_case):
        """Test chat format examples."""
        prompt = learning_service.build_few_shot_prompt(
            base_prompt="You are an assistant.",
            scenario="it_triage",
            input_text="My computer is slow",
            example_format="chat",
        )
        assert "User:" in prompt or "Learning Examples" in prompt

    def test_build_few_shot_prompt_structured_format(self, learning_service, approved_case):
        """Test structured format examples."""
        prompt = learning_service.build_few_shot_prompt(
            base_prompt="You are an assistant.",
            scenario="it_triage",
            input_text="My computer is slow",
            example_format="structured",
        )
        assert "Learning Examples" in prompt

    # Effectiveness tests
    def test_record_effectiveness(self, learning_service, approved_case):
        """Test recording effectiveness."""
        case = learning_service.record_effectiveness(
            case_id=approved_case.id,
            was_helpful=True,
            score=0.9,
        )
        assert case is not None
        assert case.effectiveness_score > 0

    def test_record_effectiveness_not_found(self, learning_service):
        """Test effectiveness for non-existent case."""
        result = learning_service.record_effectiveness(
            case_id=uuid4(),
            was_helpful=True,
        )
        assert result is None

    # Statistics tests
    def test_get_statistics(self, learning_service, sample_case):
        """Test getting statistics."""
        stats = learning_service.get_statistics()
        assert stats.total_cases >= 1
        assert "it_triage" in stats.by_scenario

    def test_get_scenario_statistics(self, learning_service, sample_case):
        """Test scenario-specific statistics."""
        stats = learning_service.get_scenario_statistics("it_triage")
        assert stats["scenario"] == "it_triage"
        assert stats["total_cases"] >= 1

    # Event handler tests
    def test_on_case_created_handler(self, learning_service):
        """Test case created event handler."""
        events = []

        def handler(case):
            events.append(case.id)

        learning_service.on_case_created(handler)

        case = learning_service.record_correction(
            scenario="test",
            original_input="test",
            original_output="test",
            corrected_output="test",
            feedback="test",
        )

        assert case.id in events

    def test_on_case_approved_handler(self, learning_service, sample_case):
        """Test case approved event handler."""
        events = []

        def handler(case):
            events.append(case.id)

        learning_service.on_case_approved(handler)

        learning_service.approve_case(sample_case.id)

        assert sample_case.id in events

    # Maintenance tests
    def test_clear_cases(self, learning_service, sample_case):
        """Test clearing all cases."""
        count = learning_service.clear_cases()
        assert count >= 1
        assert learning_service.get_statistics().total_cases == 0

    def test_archive_old_cases(self, learning_service):
        """Test archiving old cases."""
        # Create a case
        case = learning_service.record_correction(
            scenario="test",
            original_input="test",
            original_output="test",
            corrected_output="test",
            feedback="test",
        )

        # Force old date
        from datetime import timedelta
        case.created_at = datetime.utcnow() - timedelta(days=100)

        archived = learning_service.archive_old_cases(days=90, min_usage=0)
        assert archived >= 1

    def test_calculate_similarity(self, learning_service):
        """Test similarity calculation."""
        # Exact match
        sim1 = learning_service._calculate_similarity("hello world", "hello world")
        assert sim1 == 1.0

        # Similar
        sim2 = learning_service._calculate_similarity("hello world", "hello there world")
        assert 0 < sim2 < 1

        # Empty strings
        sim3 = learning_service._calculate_similarity("", "hello")
        assert sim3 == 0.0


# =============================================================================
# API Tests
# =============================================================================


class TestLearningAPI:
    """Tests for Learning API endpoints."""

    @pytest.fixture
    def client(self, learning_service):
        """Create test client."""
        from fastapi import FastAPI
        from src.api.v1.learning.routes import router, set_learning_service

        app = FastAPI()
        app.include_router(router)
        set_learning_service(learning_service)

        return TestClient(app)

    def test_health_check(self, client):
        """Test GET /learning/health"""
        response = client.get("/learning/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_record_correction(self, client):
        """Test POST /learning/corrections"""
        response = client.post(
            "/learning/corrections",
            json={
                "scenario": "it_triage",
                "original_input": "My printer is not working",
                "original_output": '{"type": "network"}',
                "corrected_output": '{"type": "hardware"}',
                "feedback": "This is a hardware issue",
                "tags": ["printer", "hardware"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"] == "it_triage"
        assert data["status"] == "pending"

    def test_list_cases(self, client, sample_case):
        """Test GET /learning/cases"""
        response = client.get("/learning/cases")
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert "total" in data

    def test_list_cases_with_filters(self, client, sample_case):
        """Test GET /learning/cases with filters."""
        response = client.get("/learning/cases?scenario=it_triage&status=pending")
        assert response.status_code == 200

    def test_get_case(self, client, sample_case):
        """Test GET /learning/cases/{id}"""
        response = client.get(f"/learning/cases/{sample_case.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_case.id)

    def test_get_case_not_found(self, client):
        """Test GET /learning/cases/{id} not found."""
        response = client.get(f"/learning/cases/{uuid4()}")
        assert response.status_code == 404

    def test_delete_case(self, client, sample_case):
        """Test DELETE /learning/cases/{id}"""
        response = client.delete(f"/learning/cases/{sample_case.id}")
        assert response.status_code == 200

    def test_approve_case(self, client, sample_case):
        """Test POST /learning/cases/{id}/approve"""
        response = client.post(
            f"/learning/cases/{sample_case.id}/approve",
            json={"approved_by": "admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_reject_case(self, client, sample_case):
        """Test POST /learning/cases/{id}/reject"""
        response = client.post(
            f"/learning/cases/{sample_case.id}/reject",
            json={"reason": "Not a valid example"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_bulk_approve(self, client, learning_service):
        """Test POST /learning/cases/bulk-approve"""
        # Create cases
        cases = []
        for i in range(2):
            case = learning_service.record_correction(
                scenario="test",
                original_input=f"input {i}",
                original_output=f"output {i}",
                corrected_output=f"corrected {i}",
                feedback=f"feedback {i}",
            )
            cases.append(case)

        response = client.post(
            "/learning/cases/bulk-approve",
            json={
                "case_ids": [str(c.id) for c in cases],
                "approved_by": "admin",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approved_count"] == 2

    def test_find_similar_cases(self, client, approved_case):
        """Test POST /learning/similar"""
        response = client.post(
            "/learning/similar",
            json={
                "scenario": "it_triage",
                "input_text": "My laptop is slow",
                "limit": 5,
                "approved_only": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_build_prompt(self, client, approved_case):
        """Test POST /learning/prompt"""
        response = client.post(
            "/learning/prompt",
            json={
                "base_prompt": "You are an IT expert.",
                "scenario": "it_triage",
                "input_text": "My computer is slow",
                "example_format": "standard",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "enhanced_prompt" in data

    def test_record_effectiveness(self, client, approved_case):
        """Test POST /learning/cases/{id}/effectiveness"""
        response = client.post(
            f"/learning/cases/{approved_case.id}/effectiveness",
            json={"was_helpful": True, "score": 0.85},
        )
        assert response.status_code == 200

    def test_get_statistics(self, client, sample_case):
        """Test GET /learning/statistics"""
        response = client.get("/learning/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_cases" in data

    def test_get_scenario_statistics(self, client, sample_case):
        """Test GET /learning/scenarios/{name}/statistics"""
        response = client.get("/learning/scenarios/it_triage/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["scenario"] == "it_triage"
