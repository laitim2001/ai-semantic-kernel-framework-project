# =============================================================================
# IPA Platform - Versioning Unit Tests
# =============================================================================
# Sprint 4: Developer Experience - Template Version Management
#
# Comprehensive tests for template versioning functionality.
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.domain.versioning import (
    TemplateVersion,
    VersionDiff,
    VersioningError,
    VersioningService,
)
from src.domain.versioning.service import (
    ChangeType,
    SemanticVersion,
    VersionStatus,
)


# =============================================================================
# Semantic Version Tests
# =============================================================================


class TestSemanticVersion:
    """Test SemanticVersion class."""

    def test_str_representation(self):
        """Test string representation."""
        version = SemanticVersion(1, 2, 3)
        assert str(version) == "1.2.3"

    def test_comparison(self):
        """Test version comparison."""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(1, 0, 1)
        v3 = SemanticVersion(1, 1, 0)
        v4 = SemanticVersion(2, 0, 0)

        assert v1 < v2
        assert v2 < v3
        assert v3 < v4
        assert not v4 < v1

    def test_equality(self):
        """Test version equality."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)
        v3 = SemanticVersion(1, 2, 4)

        assert v1 == v2
        assert v1 != v3

    def test_increment_patch(self):
        """Test patch increment."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.increment(ChangeType.PATCH)

        assert str(new_version) == "1.2.4"

    def test_increment_minor(self):
        """Test minor increment."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.increment(ChangeType.MINOR)

        assert str(new_version) == "1.3.0"

    def test_increment_major(self):
        """Test major increment."""
        version = SemanticVersion(1, 2, 3)
        new_version = version.increment(ChangeType.MAJOR)

        assert str(new_version) == "2.0.0"

    def test_parse_valid(self):
        """Test parsing valid version string."""
        version = SemanticVersion.parse("1.2.3")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_parse_invalid(self):
        """Test parsing invalid version string."""
        with pytest.raises(ValueError):
            SemanticVersion.parse("invalid")

        with pytest.raises(ValueError):
            SemanticVersion.parse("1.2")

        with pytest.raises(ValueError):
            SemanticVersion.parse("1.2.3.4")


# =============================================================================
# Versioning Service Tests
# =============================================================================


class TestVersioningService:
    """Test VersioningService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = VersioningService()
        self.template_id = "test_template"
        self.content = {
            "name": "Test Template",
            "description": "A test template",
            "parameters": {"param1": "value1"},
        }

    def teardown_method(self):
        """Clean up after tests."""
        self.service.clear_all()

    # =========================================================================
    # Version Creation Tests
    # =========================================================================

    def test_create_first_version(self):
        """Test creating first version."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
            changelog="Initial version",
            created_by="test_user",
        )

        assert version is not None
        assert version.template_id == self.template_id
        assert str(version.version) == "1.0.0"
        assert version.status == VersionStatus.DRAFT
        assert version.changelog == "Initial version"
        assert version.created_by == "test_user"

    def test_create_patch_version(self):
        """Test creating patch version."""
        self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        version = self.service.create_version(
            template_id=self.template_id,
            content={"name": "Updated"},
            change_type=ChangeType.PATCH,
        )

        assert str(version.version) == "1.0.1"

    def test_create_minor_version(self):
        """Test creating minor version."""
        self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        version = self.service.create_version(
            template_id=self.template_id,
            content={"name": "Updated"},
            change_type=ChangeType.MINOR,
        )

        assert str(version.version) == "1.1.0"

    def test_create_major_version(self):
        """Test creating major version."""
        self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        version = self.service.create_version(
            template_id=self.template_id,
            content={"name": "Updated"},
            change_type=ChangeType.MAJOR,
        )

        assert str(version.version) == "2.0.0"

    def test_create_version_with_tags(self):
        """Test creating version with tags."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
            tags=["stable", "production"],
        )

        assert "stable" in version.tags
        assert "production" in version.tags

    # =========================================================================
    # Version Retrieval Tests
    # =========================================================================

    def test_get_version(self):
        """Test getting version by ID."""
        created = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        version = self.service.get_version(created.id)

        assert version is not None
        assert version.id == created.id

    def test_get_version_not_found(self):
        """Test getting non-existent version."""
        version = self.service.get_version(uuid4())
        assert version is None

    def test_get_version_by_string(self):
        """Test getting version by version string."""
        self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        version = self.service.get_version_by_string(self.template_id, "1.0.0")

        assert version is not None
        assert str(version.version) == "1.0.0"

    def test_get_version_by_string_not_found(self):
        """Test getting non-existent version by string."""
        version = self.service.get_version_by_string(self.template_id, "99.99.99")
        assert version is None

    def test_get_latest_version(self):
        """Test getting latest version."""
        self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        self.service.create_version(
            template_id=self.template_id,
            content={"name": "v2"},
            change_type=ChangeType.MINOR,
        )

        latest = self.service.get_latest_version(self.template_id)

        assert latest is not None
        assert str(latest.version) == "1.1.0"

    def test_get_latest_version_with_status(self):
        """Test getting latest version with status filter."""
        v1 = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        self.service.publish_version(v1.id)

        self.service.create_version(
            template_id=self.template_id,
            content={"name": "v2"},
            change_type=ChangeType.MINOR,
        )

        latest_published = self.service.get_latest_version(
            self.template_id,
            status=VersionStatus.PUBLISHED,
        )
        latest_draft = self.service.get_latest_version(
            self.template_id,
            status=VersionStatus.DRAFT,
        )

        assert str(latest_published.version) == "1.0.0"
        assert str(latest_draft.version) == "1.1.0"

    def test_get_latest_version_no_versions(self):
        """Test getting latest version when none exist."""
        latest = self.service.get_latest_version("nonexistent")
        assert latest is None

    def test_list_versions(self):
        """Test listing versions."""
        for i in range(5):
            self.service.create_version(
                template_id=self.template_id,
                content={"version": i},
                change_type=ChangeType.PATCH,
            )

        versions = self.service.list_versions(self.template_id)

        assert len(versions) == 5

    def test_list_versions_with_limit(self):
        """Test listing versions with limit."""
        for i in range(5):
            self.service.create_version(
                template_id=self.template_id,
                content={"version": i},
                change_type=ChangeType.PATCH,
            )

        versions = self.service.list_versions(self.template_id, limit=3)

        assert len(versions) == 3

    def test_list_versions_with_status(self):
        """Test listing versions with status filter."""
        v1 = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        self.service.publish_version(v1.id)

        self.service.create_version(
            template_id=self.template_id,
            content={"name": "v2"},
            change_type=ChangeType.MINOR,
        )

        published = self.service.list_versions(
            self.template_id,
            status=VersionStatus.PUBLISHED,
        )
        drafts = self.service.list_versions(
            self.template_id,
            status=VersionStatus.DRAFT,
        )

        assert len(published) == 1
        assert len(drafts) == 1

    # =========================================================================
    # Version Deletion Tests
    # =========================================================================

    def test_delete_draft_version(self):
        """Test deleting draft version."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        result = self.service.delete_version(version.id)

        assert result is True
        assert self.service.get_version(version.id) is None

    def test_delete_published_version(self):
        """Test deleting published version fails."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        self.service.publish_version(version.id)

        with pytest.raises(VersioningError):
            self.service.delete_version(version.id)

    def test_delete_version_not_found(self):
        """Test deleting non-existent version."""
        result = self.service.delete_version(uuid4())
        assert result is False

    # =========================================================================
    # Status Management Tests
    # =========================================================================

    def test_publish_version(self):
        """Test publishing version."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        published = self.service.publish_version(version.id, "admin")

        assert published is not None
        assert published.status == VersionStatus.PUBLISHED
        assert published.metadata["published_by"] == "admin"

    def test_publish_already_published(self):
        """Test publishing already published version fails."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        self.service.publish_version(version.id)

        with pytest.raises(VersioningError):
            self.service.publish_version(version.id)

    def test_publish_deprecates_previous(self):
        """Test publishing deprecates previous published version."""
        v1 = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        self.service.publish_version(v1.id)

        v2 = self.service.create_version(
            template_id=self.template_id,
            content={"name": "v2"},
            change_type=ChangeType.MINOR,
        )
        self.service.publish_version(v2.id)

        # v1 should now be deprecated
        v1_updated = self.service.get_version(v1.id)
        assert v1_updated.status == VersionStatus.DEPRECATED

    def test_deprecate_version(self):
        """Test deprecating version."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        deprecated = self.service.deprecate_version(version.id, "No longer needed")

        assert deprecated is not None
        assert deprecated.status == VersionStatus.DEPRECATED
        assert deprecated.metadata["deprecation_reason"] == "No longer needed"

    def test_archive_version(self):
        """Test archiving version."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        archived = self.service.archive_version(version.id)

        assert archived is not None
        assert archived.status == VersionStatus.ARCHIVED

    # =========================================================================
    # Diff Tests
    # =========================================================================

    def test_compare_versions(self):
        """Test comparing two versions."""
        v1 = self.service.create_version(
            template_id=self.template_id,
            content={"name": "Original", "value": 1},
        )
        v2 = self.service.create_version(
            template_id=self.template_id,
            content={"name": "Updated", "value": 1},
            change_type=ChangeType.PATCH,
        )

        diff = self.service.compare_versions(v1.id, v2.id)

        assert diff.old_version == "1.0.0"
        assert diff.new_version == "1.0.1"
        assert "name" in diff.affected_fields

    def test_compare_versions_from_nothing(self):
        """Test comparing version to nothing."""
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        diff = self.service.compare_versions(None, version.id)

        assert diff.old_version is None
        assert diff.new_version == "1.0.0"
        assert diff.summary["additions"] > 0

    def test_compare_versions_not_found(self):
        """Test comparing with non-existent version."""
        with pytest.raises(VersioningError):
            self.service.compare_versions(None, uuid4())

    # =========================================================================
    # Rollback Tests
    # =========================================================================

    def test_rollback(self):
        """Test rollback to previous version."""
        v1 = self.service.create_version(
            template_id=self.template_id,
            content={"name": "v1"},
        )
        self.service.create_version(
            template_id=self.template_id,
            content={"name": "v2"},
            change_type=ChangeType.MINOR,
        )

        rollback_version = self.service.rollback(
            template_id=self.template_id,
            target_version_id=v1.id,
            created_by="admin",
        )

        assert rollback_version.content["name"] == "v1"
        assert "Rollback to version" in rollback_version.changelog

    def test_rollback_wrong_template(self):
        """Test rollback to version from different template fails."""
        v1 = self.service.create_version(
            template_id="template_a",
            content={"name": "v1"},
        )

        with pytest.raises(VersioningError):
            self.service.rollback(
                template_id="template_b",
                target_version_id=v1.id,
            )

    def test_rollback_version_not_found(self):
        """Test rollback to non-existent version fails."""
        with pytest.raises(VersioningError):
            self.service.rollback(
                template_id=self.template_id,
                target_version_id=uuid4(),
            )

    # =========================================================================
    # Statistics Tests
    # =========================================================================

    def test_get_statistics(self):
        """Test getting statistics."""
        # Create versions for multiple templates
        for tmpl_id in ["template_a", "template_b"]:
            for i in range(3):
                self.service.create_version(
                    template_id=tmpl_id,
                    content={"version": i},
                    change_type=ChangeType.PATCH,
                )

        stats = self.service.get_statistics()

        assert stats.total_templates == 2
        assert stats.total_versions == 6
        assert "draft" in stats.versions_by_status
        assert stats.avg_versions_per_template == 3.0

    def test_get_template_statistics(self):
        """Test getting template statistics."""
        for i in range(5):
            self.service.create_version(
                template_id=self.template_id,
                content={"version": i},
                change_type=ChangeType.PATCH,
            )

        stats = self.service.get_template_statistics(self.template_id)

        assert stats["template_id"] == self.template_id
        assert stats["total_versions"] == 5
        assert stats["latest_version"] == "1.0.4"

    def test_get_template_statistics_no_versions(self):
        """Test getting statistics for template with no versions."""
        stats = self.service.get_template_statistics("nonexistent")

        assert stats["total_versions"] == 0
        assert stats["current_version"] is None

    # =========================================================================
    # Event Handler Tests
    # =========================================================================

    def test_version_created_handler(self):
        """Test version created event handler."""
        created_versions = []

        def handler(version):
            created_versions.append(version)

        self.service.on_version_created(handler)
        self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )

        assert len(created_versions) == 1

    def test_version_published_handler(self):
        """Test version published event handler."""
        published_versions = []

        def handler(version):
            published_versions.append(version)

        self.service.on_version_published(handler)
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        self.service.publish_version(version.id)

        assert len(published_versions) == 1

    def test_handler_error_isolation(self):
        """Test that handler errors don't affect versioning."""
        def bad_handler(version):
            raise Exception("Handler error")

        self.service.on_version_created(bad_handler)

        # Should not raise
        version = self.service.create_version(
            template_id=self.template_id,
            content=self.content,
        )
        assert version is not None

    # =========================================================================
    # Utility Tests
    # =========================================================================

    def test_clear_all(self):
        """Test clearing all versions."""
        for i in range(5):
            self.service.create_version(
                template_id=self.template_id,
                content={"version": i},
            )

        assert self.service.get_version_count() == 5

        self.service.clear_all()

        assert self.service.get_version_count() == 0


# =============================================================================
# API Tests
# =============================================================================


class TestVersioningAPI:
    """Test Versioning API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from main import app
        from src.api.v1.versioning.routes import set_versioning_service

        # Create fresh service for each test
        service = VersioningService()
        set_versioning_service(service)

        with TestClient(app) as client:
            yield client

        # Cleanup
        service.clear_all()

    @pytest.fixture
    def template_id(self):
        """Return template ID."""
        return "test_template"

    @pytest.fixture
    def content(self):
        """Return test content."""
        return {"name": "Test", "value": 123}

    # =========================================================================
    # Health Check Tests
    # =========================================================================

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/versions/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "versioning"
        assert data["status"] == "healthy"

    # =========================================================================
    # Version Management Tests
    # =========================================================================

    def test_create_version_api(self, client, template_id, content):
        """Test create version endpoint."""
        response = client.post(
            "/api/v1/versions/",
            json={
                "template_id": template_id,
                "content": content,
                "change_type": "minor",
                "changelog": "Test version",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["template_id"] == template_id
        assert data["version"] == "1.0.0"

    def test_create_version_invalid_change_type(self, client, template_id, content):
        """Test create version with invalid change type."""
        response = client.post(
            "/api/v1/versions/",
            json={
                "template_id": template_id,
                "content": content,
                "change_type": "invalid",
            },
        )

        assert response.status_code == 400

    def test_get_version_api(self, client, template_id, content):
        """Test get version endpoint."""
        # Create version
        create_response = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": content},
        )
        version_id = create_response.json()["id"]

        response = client.get(f"/api/v1/versions/{version_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == version_id
        assert "content" in data

    def test_get_version_not_found(self, client):
        """Test get non-existent version."""
        response = client.get(f"/api/v1/versions/{uuid4()}")
        assert response.status_code == 404

    def test_delete_version_api(self, client, template_id, content):
        """Test delete version endpoint."""
        create_response = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": content},
        )
        version_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/versions/{version_id}")
        assert response.status_code == 200

        response = client.get(f"/api/v1/versions/{version_id}")
        assert response.status_code == 404

    def test_list_versions_api(self, client, template_id, content):
        """Test list versions endpoint."""
        for i in range(3):
            client.post(
                "/api/v1/versions/",
                json={"template_id": template_id, "content": {"v": i}},
            )

        response = client.get("/api/v1/versions/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    # =========================================================================
    # Status Management Tests
    # =========================================================================

    def test_publish_version_api(self, client, template_id, content):
        """Test publish version endpoint."""
        create_response = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": content},
        )
        version_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/versions/{version_id}/publish",
            json={"published_by": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"

    def test_deprecate_version_api(self, client, template_id, content):
        """Test deprecate version endpoint."""
        create_response = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": content},
        )
        version_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/versions/{version_id}/deprecate",
            json={"reason": "No longer needed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deprecated"

    def test_archive_version_api(self, client, template_id, content):
        """Test archive version endpoint."""
        create_response = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": content},
        )
        version_id = create_response.json()["id"]

        response = client.post(f"/api/v1/versions/{version_id}/archive")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

    # =========================================================================
    # Template Endpoints Tests
    # =========================================================================

    def test_list_template_versions_api(self, client, template_id, content):
        """Test list template versions endpoint."""
        for i in range(3):
            client.post(
                "/api/v1/versions/",
                json={"template_id": template_id, "content": {"v": i}},
            )

        response = client.get(f"/api/v1/versions/templates/{template_id}/versions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_get_latest_version_api(self, client, template_id, content):
        """Test get latest version endpoint."""
        for i in range(3):
            client.post(
                "/api/v1/versions/",
                json={"template_id": template_id, "content": {"v": i}},
            )

        response = client.get(f"/api/v1/versions/templates/{template_id}/latest")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.2"

    def test_rollback_api(self, client, template_id, content):
        """Test rollback endpoint."""
        create_response = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": {"name": "v1"}},
        )
        v1_id = create_response.json()["id"]

        client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": {"name": "v2"}},
        )

        response = client.post(
            f"/api/v1/versions/templates/{template_id}/rollback",
            json={"target_version_id": v1_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "Rollback" in data["changelog"]

    def test_get_template_statistics_api(self, client, template_id, content):
        """Test get template statistics endpoint."""
        for i in range(3):
            client.post(
                "/api/v1/versions/",
                json={"template_id": template_id, "content": {"v": i}},
            )

        response = client.get(
            f"/api/v1/versions/templates/{template_id}/statistics"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_versions"] == 3

    # =========================================================================
    # Compare Tests
    # =========================================================================

    def test_compare_versions_api(self, client, template_id):
        """Test compare versions endpoint."""
        r1 = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": {"name": "v1"}},
        )
        v1_id = r1.json()["id"]

        r2 = client.post(
            "/api/v1/versions/",
            json={"template_id": template_id, "content": {"name": "v2"}},
        )
        v2_id = r2.json()["id"]

        response = client.post(
            "/api/v1/versions/compare",
            json={"old_version_id": v1_id, "new_version_id": v2_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["old_version"] == "1.0.0"
        assert data["new_version"] == "1.0.1"

    def test_get_statistics_api(self, client, template_id, content):
        """Test get statistics endpoint."""
        for i in range(3):
            client.post(
                "/api/v1/versions/",
                json={"template_id": template_id, "content": {"v": i}},
            )

        response = client.get("/api/v1/versions/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_versions"] == 3
