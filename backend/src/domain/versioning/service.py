# =============================================================================
# IPA Platform - Template Versioning Service
# =============================================================================
# Sprint 4: Developer Experience - Template Version Management
#
# Version control service for agent templates with:
#   - Semantic versioning (major.minor.patch)
#   - Version history tracking
#   - Version comparison (diff)
#   - Rollback support
#   - Branch management (future)
#
# Author: IPA Platform Team
# Created: 2025-11-30
# =============================================================================

import difflib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class VersionStatus(str, Enum):
    """Version status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ChangeType(str, Enum):
    """Type of change in a version."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SemanticVersion:
    """Semantic version (major.minor.patch)."""

    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        """String representation."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "SemanticVersion") -> bool:
        """Less than comparison."""
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )

    def increment(self, change_type: ChangeType) -> "SemanticVersion":
        """Increment version based on change type."""
        if change_type == ChangeType.MAJOR:
            return SemanticVersion(self.major + 1, 0, 0)
        elif change_type == ChangeType.MINOR:
            return SemanticVersion(self.major, self.minor + 1, 0)
        else:  # PATCH
            return SemanticVersion(self.major, self.minor, self.patch + 1)

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """Parse version string."""
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
        )


@dataclass
class TemplateVersion:
    """A version of a template."""

    id: UUID
    template_id: str
    version: SemanticVersion
    content: Dict[str, Any]
    status: VersionStatus
    created_at: datetime
    created_by: Optional[str] = None
    changelog: str = ""
    parent_version_id: Optional[UUID] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def version_string(self) -> str:
        """Get version as string."""
        return str(self.version)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "template_id": self.template_id,
            "version": str(self.version),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "changelog": self.changelog,
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class DiffLine:
    """A single line in a diff."""

    type: str  # 'add', 'remove', 'context'
    content: str
    old_line: Optional[int] = None
    new_line: Optional[int] = None


@dataclass
class DiffHunk:
    """A hunk of changes in a diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[DiffLine] = field(default_factory=list)


@dataclass
class VersionDiff:
    """Difference between two versions."""

    old_version: Optional[str]
    new_version: str
    changes: List[DiffHunk]
    summary: Dict[str, int]  # additions, deletions, modifications
    affected_fields: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "old_version": self.old_version,
            "new_version": self.new_version,
            "changes": [
                {
                    "old_start": h.old_start,
                    "old_count": h.old_count,
                    "new_start": h.new_start,
                    "new_count": h.new_count,
                    "lines": [
                        {
                            "type": line.type,
                            "content": line.content,
                            "old_line": line.old_line,
                            "new_line": line.new_line,
                        }
                        for line in h.lines
                    ],
                }
                for h in self.changes
            ],
            "summary": self.summary,
            "affected_fields": self.affected_fields,
        }


@dataclass
class VersionStatistics:
    """Statistics for versioning."""

    total_templates: int
    total_versions: int
    versions_by_status: Dict[str, int]
    avg_versions_per_template: float
    recent_versions: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_templates": self.total_templates,
            "total_versions": self.total_versions,
            "versions_by_status": self.versions_by_status,
            "avg_versions_per_template": self.avg_versions_per_template,
            "recent_versions": self.recent_versions,
        }


# =============================================================================
# Exceptions
# =============================================================================


class VersioningError(Exception):
    """Base exception for versioning errors."""

    pass


# =============================================================================
# Versioning Service
# =============================================================================


class VersioningService:
    """
    Template versioning service.

    Provides version control for agent templates with:
    - Semantic versioning
    - Version history
    - Diff generation
    - Rollback support
    """

    def __init__(self):
        """Initialize the versioning service."""
        # In-memory storage (production would use database)
        self._versions: Dict[UUID, TemplateVersion] = {}
        self._template_versions: Dict[str, List[UUID]] = {}  # template_id -> version_ids
        self._event_handlers: Dict[str, List[Callable]] = {}

    # =========================================================================
    # Version Management
    # =========================================================================

    def create_version(
        self,
        template_id: str,
        content: Dict[str, Any],
        change_type: ChangeType = ChangeType.PATCH,
        changelog: str = "",
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TemplateVersion:
        """Create a new version of a template."""
        # Get current latest version
        latest = self.get_latest_version(template_id)

        # Calculate new version number
        if latest:
            new_version = latest.version.increment(change_type)
            parent_id = latest.id
        else:
            new_version = SemanticVersion(1, 0, 0)
            parent_id = None

        # Create version
        version = TemplateVersion(
            id=uuid4(),
            template_id=template_id,
            version=new_version,
            content=content,
            status=VersionStatus.DRAFT,
            created_at=datetime.utcnow(),
            created_by=created_by,
            changelog=changelog,
            parent_version_id=parent_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Store
        self._versions[version.id] = version

        if template_id not in self._template_versions:
            self._template_versions[template_id] = []
        self._template_versions[template_id].append(version.id)

        # Notify handlers
        self._notify_handlers("version_created", version)

        return version

    def get_version(self, version_id: UUID) -> Optional[TemplateVersion]:
        """Get a version by ID."""
        return self._versions.get(version_id)

    def get_version_by_string(
        self,
        template_id: str,
        version_string: str,
    ) -> Optional[TemplateVersion]:
        """Get a version by template ID and version string."""
        version_ids = self._template_versions.get(template_id, [])

        for vid in version_ids:
            version = self._versions.get(vid)
            if version and str(version.version) == version_string:
                return version

        return None

    def get_latest_version(
        self,
        template_id: str,
        status: Optional[VersionStatus] = None,
    ) -> Optional[TemplateVersion]:
        """Get the latest version of a template."""
        version_ids = self._template_versions.get(template_id, [])

        if not version_ids:
            return None

        # Get all versions and find latest
        versions = [self._versions.get(vid) for vid in version_ids]
        versions = [v for v in versions if v is not None]

        if status:
            versions = [v for v in versions if v.status == status]

        if not versions:
            return None

        # Sort by version (newest first)
        versions.sort(key=lambda v: v.version, reverse=True)

        return versions[0]

    def list_versions(
        self,
        template_id: str,
        status: Optional[VersionStatus] = None,
        limit: int = 100,
    ) -> List[TemplateVersion]:
        """List versions of a template."""
        version_ids = self._template_versions.get(template_id, [])

        versions = [self._versions.get(vid) for vid in version_ids]
        versions = [v for v in versions if v is not None]

        if status:
            versions = [v for v in versions if v.status == status]

        # Sort by version (newest first)
        versions.sort(key=lambda v: v.version, reverse=True)

        return versions[:limit]

    def delete_version(self, version_id: UUID) -> bool:
        """Delete a version."""
        version = self._versions.get(version_id)
        if not version:
            return False

        # Can only delete drafts
        if version.status != VersionStatus.DRAFT:
            raise VersioningError("Can only delete draft versions")

        # Remove from storage
        del self._versions[version_id]

        if version.template_id in self._template_versions:
            self._template_versions[version.template_id] = [
                vid for vid in self._template_versions[version.template_id]
                if vid != version_id
            ]

        return True

    # =========================================================================
    # Status Management
    # =========================================================================

    def publish_version(
        self,
        version_id: UUID,
        published_by: Optional[str] = None,
    ) -> Optional[TemplateVersion]:
        """Publish a version."""
        version = self._versions.get(version_id)
        if not version:
            return None

        if version.status != VersionStatus.DRAFT:
            raise VersioningError("Only draft versions can be published")

        # Deprecate current published version
        current_published = self.get_latest_version(
            version.template_id,
            status=VersionStatus.PUBLISHED,
        )
        if current_published:
            current_published.status = VersionStatus.DEPRECATED

        # Publish new version
        version.status = VersionStatus.PUBLISHED
        version.metadata["published_by"] = published_by
        version.metadata["published_at"] = datetime.utcnow().isoformat()

        self._notify_handlers("version_published", version)

        return version

    def deprecate_version(
        self,
        version_id: UUID,
        reason: str = "",
    ) -> Optional[TemplateVersion]:
        """Deprecate a version."""
        version = self._versions.get(version_id)
        if not version:
            return None

        version.status = VersionStatus.DEPRECATED
        version.metadata["deprecation_reason"] = reason
        version.metadata["deprecated_at"] = datetime.utcnow().isoformat()

        return version

    def archive_version(self, version_id: UUID) -> Optional[TemplateVersion]:
        """Archive a version."""
        version = self._versions.get(version_id)
        if not version:
            return None

        version.status = VersionStatus.ARCHIVED
        version.metadata["archived_at"] = datetime.utcnow().isoformat()

        return version

    # =========================================================================
    # Diff and Comparison
    # =========================================================================

    def compare_versions(
        self,
        old_version_id: Optional[UUID],
        new_version_id: UUID,
    ) -> VersionDiff:
        """Compare two versions."""
        new_version = self._versions.get(new_version_id)
        if not new_version:
            raise VersioningError(f"Version not found: {new_version_id}")

        old_content = ""
        old_version_str = None

        if old_version_id:
            old_version = self._versions.get(old_version_id)
            if old_version:
                old_content = json.dumps(old_version.content, indent=2, sort_keys=True)
                old_version_str = str(old_version.version)

        new_content = json.dumps(new_version.content, indent=2, sort_keys=True)

        # Generate diff
        hunks = self._generate_diff(old_content, new_content)

        # Calculate summary
        additions = sum(
            len([l for l in h.lines if l.type == "add"])
            for h in hunks
        )
        deletions = sum(
            len([l for l in h.lines if l.type == "remove"])
            for h in hunks
        )

        # Find affected fields
        affected_fields = self._find_affected_fields(
            json.loads(old_content) if old_content else {},
            new_version.content,
        )

        return VersionDiff(
            old_version=old_version_str,
            new_version=str(new_version.version),
            changes=hunks,
            summary={
                "additions": additions,
                "deletions": deletions,
                "modifications": len(hunks),
            },
            affected_fields=affected_fields,
        )

    def _generate_diff(self, old: str, new: str) -> List[DiffHunk]:
        """Generate unified diff."""
        old_lines = old.splitlines(keepends=True) if old else []
        new_lines = new.splitlines(keepends=True)

        hunks: List[DiffHunk] = []
        differ = difflib.unified_diff(old_lines, new_lines, lineterm="")

        current_hunk: Optional[DiffHunk] = None
        old_line = 0
        new_line = 0

        for line in differ:
            if line.startswith("@@"):
                # Parse hunk header
                match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    if current_hunk:
                        hunks.append(current_hunk)

                    current_hunk = DiffHunk(
                        old_start=int(match.group(1)),
                        old_count=int(match.group(2) or 1),
                        new_start=int(match.group(3)),
                        new_count=int(match.group(4) or 1),
                    )
                    old_line = int(match.group(1))
                    new_line = int(match.group(3))

            elif line.startswith("---") or line.startswith("+++"):
                continue

            elif current_hunk:
                content = line[1:] if len(line) > 1 else ""

                if line.startswith("-"):
                    current_hunk.lines.append(DiffLine(
                        type="remove",
                        content=content,
                        old_line=old_line,
                    ))
                    old_line += 1

                elif line.startswith("+"):
                    current_hunk.lines.append(DiffLine(
                        type="add",
                        content=content,
                        new_line=new_line,
                    ))
                    new_line += 1

                else:
                    current_hunk.lines.append(DiffLine(
                        type="context",
                        content=content,
                        old_line=old_line,
                        new_line=new_line,
                    ))
                    old_line += 1
                    new_line += 1

        if current_hunk:
            hunks.append(current_hunk)

        return hunks

    def _find_affected_fields(
        self,
        old: Dict[str, Any],
        new: Dict[str, Any],
        prefix: str = "",
    ) -> List[str]:
        """Find fields that changed between versions."""
        affected = []

        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            full_key = f"{prefix}.{key}" if prefix else key

            if key not in old:
                affected.append(full_key)
            elif key not in new:
                affected.append(full_key)
            elif old[key] != new[key]:
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    affected.extend(self._find_affected_fields(old[key], new[key], full_key))
                else:
                    affected.append(full_key)

        return affected

    # =========================================================================
    # Rollback
    # =========================================================================

    def rollback(
        self,
        template_id: str,
        target_version_id: UUID,
        created_by: Optional[str] = None,
    ) -> TemplateVersion:
        """Rollback to a previous version."""
        target = self._versions.get(target_version_id)
        if not target:
            raise VersioningError(f"Version not found: {target_version_id}")

        if target.template_id != template_id:
            raise VersioningError("Version does not belong to this template")

        # Create new version with content from target
        return self.create_version(
            template_id=template_id,
            content=target.content.copy(),
            change_type=ChangeType.MINOR,
            changelog=f"Rollback to version {target.version}",
            created_by=created_by,
            metadata={"rollback_from": str(target_version_id)},
        )

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> VersionStatistics:
        """Get versioning statistics."""
        total_templates = len(self._template_versions)
        total_versions = len(self._versions)

        # Count by status
        versions_by_status: Dict[str, int] = {}
        for version in self._versions.values():
            status = version.status.value
            versions_by_status[status] = versions_by_status.get(status, 0) + 1

        # Average versions per template
        avg_versions = (
            total_versions / total_templates if total_templates > 0 else 0
        )

        # Recent versions
        recent = sorted(
            self._versions.values(),
            key=lambda v: v.created_at,
            reverse=True,
        )[:10]

        return VersionStatistics(
            total_templates=total_templates,
            total_versions=total_versions,
            versions_by_status=versions_by_status,
            avg_versions_per_template=round(avg_versions, 2),
            recent_versions=[v.to_dict() for v in recent],
        )

    def get_template_statistics(self, template_id: str) -> Dict[str, Any]:
        """Get statistics for a specific template."""
        versions = self.list_versions(template_id)

        if not versions:
            return {
                "template_id": template_id,
                "total_versions": 0,
                "current_version": None,
                "versions_by_status": {},
            }

        # Count by status
        versions_by_status: Dict[str, int] = {}
        for version in versions:
            status = version.status.value
            versions_by_status[status] = versions_by_status.get(status, 0) + 1

        # Find current published
        published = self.get_latest_version(template_id, VersionStatus.PUBLISHED)

        return {
            "template_id": template_id,
            "total_versions": len(versions),
            "current_version": str(published.version) if published else None,
            "latest_version": str(versions[0].version),
            "versions_by_status": versions_by_status,
            "first_created": versions[-1].created_at.isoformat(),
            "last_updated": versions[0].created_at.isoformat(),
        }

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def on_version_created(
        self,
        handler: Callable[[TemplateVersion], None],
    ) -> None:
        """Register handler for version creation."""
        if "version_created" not in self._event_handlers:
            self._event_handlers["version_created"] = []
        self._event_handlers["version_created"].append(handler)

    def on_version_published(
        self,
        handler: Callable[[TemplateVersion], None],
    ) -> None:
        """Register handler for version publication."""
        if "version_published" not in self._event_handlers:
            self._event_handlers["version_published"] = []
        self._event_handlers["version_published"].append(handler)

    def _notify_handlers(
        self,
        event: str,
        version: TemplateVersion,
    ) -> None:
        """Notify all handlers for an event."""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(version)
            except Exception:
                pass  # Don't let handler errors affect versioning

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def clear_all(self) -> None:
        """Clear all versions (for testing)."""
        self._versions.clear()
        self._template_versions.clear()

    def get_version_count(self) -> int:
        """Get total version count."""
        return len(self._versions)
