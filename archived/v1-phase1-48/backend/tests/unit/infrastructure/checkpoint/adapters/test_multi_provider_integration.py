"""Integration tests for multi-provider checkpoint system.

Sprint 121 -- Tests for the UnifiedCheckpointRegistry coordinating all 4
checkpoint adapters (Hybrid, AgentFramework, Domain, SessionRecovery).

Tests cover:
    - register_all_four_providers: All 4 adapters registered, list_providers returns 4
    - save_load_across_providers: Save and load through the registry for each provider
    - list_all_returns_all_providers: registry.list_all() returns dict with all providers
    - cleanup_expired_across_providers: registry.cleanup_expired() runs on all providers
    - get_stats: registry.get_stats() returns stats for all providers
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.sessions.recovery import (
    CheckpointType as SessionCheckpointType,
    SessionCheckpoint,
    SessionRecoveryManager,
)
from src.domain.checkpoints.storage import DatabaseCheckpointStorage
from src.infrastructure.checkpoint.protocol import CheckpointEntry
from src.infrastructure.checkpoint.unified_registry import UnifiedCheckpointRegistry
from src.integrations.agent_framework.multiturn.checkpoint_storage import (
    BaseCheckpointStorage,
)
from src.integrations.hybrid.checkpoint.models import (
    CheckpointStatus,
    CheckpointType,
    HybridCheckpoint,
)
from src.integrations.hybrid.checkpoint.storage import (
    CheckpointQuery,
    UnifiedCheckpointStorage,
)
from src.infrastructure.checkpoint.adapters.agent_framework_adapter import (
    AgentFrameworkCheckpointAdapter,
)
from src.infrastructure.checkpoint.adapters.domain_adapter import DomainCheckpointAdapter
from src.infrastructure.checkpoint.adapters.hybrid_adapter import HybridCheckpointAdapter
from src.infrastructure.checkpoint.adapters.session_recovery_adapter import (
    SessionRecoveryCheckpointAdapter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN_EXEC_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_DOMAIN_CP_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_hybrid_storage() -> MagicMock:
    """Create a mock UnifiedCheckpointStorage for hybrid adapter."""
    storage = MagicMock(spec=UnifiedCheckpointStorage)
    storage.save = AsyncMock(return_value="hybrid-cp-001")
    storage.load = AsyncMock(return_value=None)
    storage.delete = AsyncMock(return_value=True)
    storage.query = AsyncMock(return_value=[])
    return storage


def _make_af_storage() -> MagicMock:
    """Create a mock BaseCheckpointStorage for agent framework adapter."""
    storage = MagicMock(spec=BaseCheckpointStorage)
    storage.save = AsyncMock(return_value=None)
    storage.load = AsyncMock(return_value=None)
    storage.delete = AsyncMock(return_value=True)
    storage.list = AsyncMock(return_value=[])
    return storage


def _make_domain_storage() -> MagicMock:
    """Create a mock DatabaseCheckpointStorage for domain adapter."""
    storage = MagicMock(spec=DatabaseCheckpointStorage)
    storage.save_checkpoint = AsyncMock(return_value=_DOMAIN_CP_UUID)
    storage.load_checkpoint = AsyncMock(return_value=None)
    storage.list_checkpoints = AsyncMock(return_value=[])
    storage.delete_checkpoint = AsyncMock(return_value=True)
    return storage


def _make_recovery_manager() -> MagicMock:
    """Create a mock SessionRecoveryManager for session recovery adapter."""
    manager = MagicMock(spec=SessionRecoveryManager)
    manager.save_checkpoint = AsyncMock(return_value=None)
    manager.get_checkpoint = AsyncMock(return_value=None)
    manager.delete_checkpoint = AsyncMock(return_value=None)
    return manager


def _make_hybrid_checkpoint(
    checkpoint_id: str = "hcp-001",
    session_id: str = "sess-h",
) -> HybridCheckpoint:
    """Create a HybridCheckpoint for testing."""
    return HybridCheckpoint(
        checkpoint_id=checkpoint_id,
        session_id=session_id,
        execution_mode="chat",
        checkpoint_type=CheckpointType.AUTO,
        status=CheckpointStatus.ACTIVE,
        metadata={"unified_data": {"provider": "hybrid"}},
        created_at=datetime.utcnow(),
        expires_at=None,
    )


def _make_session_checkpoint(
    session_id: str = "sess-r",
) -> SessionCheckpoint:
    """Create a SessionCheckpoint for testing."""
    return SessionCheckpoint(
        session_id=session_id,
        checkpoint_type=SessionCheckpointType.EXECUTION_START,
        execution_id="exec-r",
        state={"provider": "session_recovery"},
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        metadata={},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hybrid_storage():
    """Mock hybrid storage."""
    return _make_hybrid_storage()


@pytest.fixture
def af_storage():
    """Mock agent framework storage."""
    return _make_af_storage()


@pytest.fixture
def domain_storage():
    """Mock domain storage."""
    return _make_domain_storage()


@pytest.fixture
def recovery_manager():
    """Mock session recovery manager."""
    return _make_recovery_manager()


@pytest.fixture
def hybrid_adapter(hybrid_storage):
    """Create HybridCheckpointAdapter."""
    return HybridCheckpointAdapter(storage=hybrid_storage, name="hybrid")


@pytest.fixture
def af_adapter(af_storage):
    """Create AgentFrameworkCheckpointAdapter."""
    return AgentFrameworkCheckpointAdapter(storage=af_storage, name="agent_framework")


@pytest.fixture
def domain_adapter(domain_storage):
    """Create DomainCheckpointAdapter."""
    return DomainCheckpointAdapter(storage=domain_storage, name="domain")


@pytest.fixture
def recovery_adapter(recovery_manager):
    """Create SessionRecoveryCheckpointAdapter."""
    return SessionRecoveryCheckpointAdapter(
        manager=recovery_manager, name="session_recovery"
    )


@pytest.fixture
async def registry(hybrid_adapter, af_adapter, domain_adapter, recovery_adapter):
    """Create a UnifiedCheckpointRegistry with all 4 providers registered."""
    reg = UnifiedCheckpointRegistry()
    await reg.register_provider(hybrid_adapter)
    await reg.register_provider(af_adapter)
    await reg.register_provider(domain_adapter)
    await reg.register_provider(recovery_adapter)
    return reg


# =========================================================================
# Registration
# =========================================================================


class TestRegistration:
    """Tests for registering all providers with the UnifiedCheckpointRegistry."""

    @pytest.mark.asyncio
    async def test_register_all_four_providers(self, registry):
        """Register all 4 adapters and verify list_providers returns 4 names."""
        providers = registry.list_providers()

        assert len(providers) == 4
        assert "hybrid" in providers
        assert "agent_framework" in providers
        assert "domain" in providers
        assert "session_recovery" in providers


# =========================================================================
# Save / Load across providers
# =========================================================================


class TestSaveLoadAcrossProviders:
    """Tests for saving and loading through the registry to each provider."""

    @pytest.mark.asyncio
    async def test_save_load_hybrid(self, registry, hybrid_storage):
        """Save and load through hybrid provider via registry."""
        save_result = await registry.save(
            provider_name="hybrid",
            checkpoint_id="cp-h-1",
            data={"mode": "chat"},
        )
        assert save_result == "hybrid-cp-001"
        hybrid_storage.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_load_agent_framework(self, registry, af_storage):
        """Save and load through agent_framework provider via registry."""
        save_result = await registry.save(
            provider_name="agent_framework",
            checkpoint_id="cp-af-1",
            data={"step": 1},
        )
        assert save_result == "cp-af-1"
        af_storage.save.assert_awaited_once()

        # Test load
        af_storage.load.return_value = {
            "unified_data": {"step": 1},
            "metadata": {},
        }
        load_result = await registry.load(
            provider_name="agent_framework",
            checkpoint_id="cp-af-1",
        )
        assert load_result == {"step": 1}

    @pytest.mark.asyncio
    async def test_save_load_domain(self, registry, domain_storage):
        """Save through domain provider via registry."""
        save_result = await registry.save(
            provider_name="domain",
            checkpoint_id="hint-id",
            data={"execution_id": str(_DOMAIN_EXEC_UUID)},
        )
        assert save_result == str(_DOMAIN_CP_UUID)
        domain_storage.save_checkpoint.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_load_session_recovery(self, registry, recovery_manager):
        """Save through session_recovery provider via registry."""
        recovery_manager.save_checkpoint.return_value = _make_session_checkpoint()

        save_result = await registry.save(
            provider_name="session_recovery",
            checkpoint_id="cp-sr-1",
            data={"checkpoint_type": "execution_start"},
        )
        assert save_result == "cp-sr-1"
        recovery_manager.save_checkpoint.assert_awaited_once()


# =========================================================================
# list_all
# =========================================================================


class TestListAll:
    """Tests for registry.list_all() across all providers."""

    @pytest.mark.asyncio
    async def test_list_all_returns_all_providers(
        self,
        registry,
        hybrid_storage,
        af_storage,
        domain_storage,
        recovery_manager,
    ):
        """Verify registry.list_all() returns a dict with all provider names."""
        # Setup mock responses
        hybrid_cp = _make_hybrid_checkpoint()
        hybrid_storage.query.return_value = [hybrid_cp]

        af_storage.list.return_value = ["af-sess-1"]
        af_storage.load.return_value = {
            "unified_data": {"key": "af"},
            "metadata": {},
        }

        # Domain returns empty (no session_id provided)
        domain_storage.list_checkpoints.return_value = []

        # Session recovery returns empty (no session_id provided)
        recovery_manager.get_checkpoint.return_value = None

        result = await registry.list_all()

        assert isinstance(result, dict)
        assert "hybrid" in result
        assert "agent_framework" in result
        assert "domain" in result
        assert "session_recovery" in result

        # Hybrid should have 1 entry
        assert len(result["hybrid"]) == 1
        # Agent framework should have 1 entry
        assert len(result["agent_framework"]) == 1


# =========================================================================
# cleanup_expired
# =========================================================================


class TestCleanupExpired:
    """Tests for registry.cleanup_expired() across all providers."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_across_providers(
        self,
        registry,
        hybrid_storage,
        af_storage,
        domain_storage,
        recovery_manager,
    ):
        """Verify cleanup_expired runs on all providers without errors."""
        # Setup: all providers return empty lists
        hybrid_storage.query.return_value = []
        af_storage.list.return_value = []
        # Domain and session_recovery return empty (no session_id)

        result = await registry.cleanup_expired(max_age_hours=24)

        assert isinstance(result, dict)
        assert "hybrid" in result
        assert "agent_framework" in result
        assert "domain" in result
        assert "session_recovery" in result

        # No deletions expected since all are empty
        for provider_name, count in result.items():
            assert count == 0


# =========================================================================
# get_stats
# =========================================================================


class TestGetStats:
    """Tests for registry.get_stats() across all providers."""

    @pytest.mark.asyncio
    async def test_get_stats(
        self,
        registry,
        hybrid_storage,
        af_storage,
        domain_storage,
        recovery_manager,
    ):
        """Verify get_stats returns statistics for all providers."""
        # Setup: all providers return empty lists
        hybrid_storage.query.return_value = []
        af_storage.list.return_value = []

        result = await registry.get_stats()

        assert result["provider_count"] == 4
        assert len(result["provider_names"]) == 4
        assert "hybrid" in result["provider_names"]
        assert "agent_framework" in result["provider_names"]
        assert "domain" in result["provider_names"]
        assert "session_recovery" in result["provider_names"]

        # Each provider should have stats
        providers_stats = result["providers"]
        for name in ["hybrid", "agent_framework", "domain", "session_recovery"]:
            assert name in providers_stats
            assert providers_stats[name]["registered"] is True
            assert "checkpoint_count" in providers_stats[name]
            assert "provider_type" in providers_stats[name]

        # Verify provider types
        assert providers_stats["hybrid"]["provider_type"] == "HybridCheckpointAdapter"
        assert (
            providers_stats["agent_framework"]["provider_type"]
            == "AgentFrameworkCheckpointAdapter"
        )
        assert providers_stats["domain"]["provider_type"] == "DomainCheckpointAdapter"
        assert (
            providers_stats["session_recovery"]["provider_type"]
            == "SessionRecoveryCheckpointAdapter"
        )
