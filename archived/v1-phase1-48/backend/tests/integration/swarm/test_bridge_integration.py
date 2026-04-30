"""
Integration tests for HybridEventBridge Swarm integration.

Tests the SwarmEventEmitter integration with HybridEventBridge.
Sprint 101: Swarm Event System + SSE Integration
"""

import pytest
from typing import List

from src.integrations.ag_ui.bridge import (
    HybridEventBridge,
    BridgeConfig,
    create_bridge,
)
from src.integrations.ag_ui.events import CustomEvent
from src.integrations.swarm.events import (
    SwarmEventEmitter,
    SwarmEventNames,
)


@pytest.fixture
def bridge_config():
    """Create a bridge config with swarm events enabled."""
    return BridgeConfig(
        chunk_size=100,
        include_metadata=True,
        enable_swarm_events=True,
        swarm_throttle_interval_ms=100,
        swarm_batch_size=3,
    )


@pytest.fixture
def collected_events():
    """Container for collected events."""
    return []


class TestBridgeSwarmConfiguration:
    """Test bridge configuration with swarm events."""

    def test_default_config_enables_swarm(self):
        """Test that default config enables swarm events."""
        config = BridgeConfig()
        assert config.enable_swarm_events is True
        assert config.swarm_throttle_interval_ms == 200
        assert config.swarm_batch_size == 5

    def test_custom_swarm_config(self, bridge_config):
        """Test custom swarm configuration."""
        assert bridge_config.swarm_throttle_interval_ms == 100
        assert bridge_config.swarm_batch_size == 3

    def test_bridge_with_swarm_config(self, bridge_config):
        """Test creating bridge with swarm configuration."""
        bridge = HybridEventBridge(config=bridge_config)

        assert bridge._config.enable_swarm_events is True
        assert bridge._swarm_emitter is None  # Not configured yet

    def test_factory_function(self):
        """Test create_bridge factory function."""
        bridge = create_bridge(chunk_size=50, include_metadata=False)

        assert bridge is not None
        assert bridge._config.chunk_size == 50
        assert bridge._config.include_metadata is False


class TestSwarmEmitterConfiguration:
    """Test swarm emitter configuration."""

    def test_configure_swarm_emitter_default(self, bridge_config):
        """Test configuring swarm emitter with defaults."""
        bridge = HybridEventBridge(config=bridge_config)

        emitter = bridge.configure_swarm_emitter()

        assert emitter is not None
        assert bridge.swarm_emitter is emitter

    def test_configure_swarm_emitter_custom_callback(self, bridge_config, collected_events):
        """Test configuring swarm emitter with custom callback."""
        bridge = HybridEventBridge(config=bridge_config)

        async def custom_callback(event: CustomEvent):
            collected_events.append(event)

        emitter = bridge.configure_swarm_emitter(event_callback=custom_callback)

        assert emitter is not None
        assert bridge.swarm_emitter is emitter

    def test_configure_swarm_emitter_custom_options(self, bridge_config):
        """Test configuring swarm emitter with custom options."""
        bridge = HybridEventBridge(config=bridge_config)

        emitter = bridge.configure_swarm_emitter(
            throttle_interval_ms=300,
            batch_size=10,
        )

        assert emitter is not None

    def test_swarm_emitter_disabled(self):
        """Test that swarm emitter is not created when disabled."""
        config = BridgeConfig(enable_swarm_events=False)
        bridge = HybridEventBridge(config=config)

        emitter = bridge.configure_swarm_emitter()

        assert emitter is None
        assert bridge.swarm_emitter is None


class TestSwarmEmitterLifecycle:
    """Test swarm emitter lifecycle in bridge."""

    @pytest.mark.asyncio
    async def test_start_stop_emitter(self, bridge_config):
        """Test starting and stopping swarm emitter."""
        bridge = HybridEventBridge(config=bridge_config)
        bridge.configure_swarm_emitter()

        await bridge.start_swarm_emitter()
        assert bridge.swarm_emitter.is_running

        await bridge.stop_swarm_emitter()
        assert not bridge.swarm_emitter.is_running

    @pytest.mark.asyncio
    async def test_start_without_configure(self, bridge_config):
        """Test starting emitter without configuring."""
        bridge = HybridEventBridge(config=bridge_config)

        # Should not raise
        await bridge.start_swarm_emitter()

    @pytest.mark.asyncio
    async def test_stop_without_start(self, bridge_config):
        """Test stopping emitter without starting."""
        bridge = HybridEventBridge(config=bridge_config)
        bridge.configure_swarm_emitter()

        # Should not raise
        await bridge.stop_swarm_emitter()


class TestSwarmEventFlow:
    """Test full swarm event flow through bridge."""

    @pytest.mark.asyncio
    async def test_event_flow_to_callback(self, bridge_config):
        """Test that events flow through to callback."""
        received_events: List[CustomEvent] = []

        async def capture_callback(event: CustomEvent):
            received_events.append(event)

        bridge = HybridEventBridge(config=bridge_config)
        emitter = bridge.configure_swarm_emitter(event_callback=capture_callback)

        await bridge.start_swarm_emitter()

        # Create a mock swarm
        from src.integrations.swarm.models import (
            AgentSwarmStatus,
            SwarmMode,
            SwarmStatus,
            WorkerExecution,
            WorkerType,
            WorkerStatus,
        )
        from datetime import datetime

        swarm = AgentSwarmStatus(
            swarm_id="test-swarm",
            mode=SwarmMode.PARALLEL,
            status=SwarmStatus.RUNNING,
            overall_progress=0,
            workers=[],
            total_tool_calls=0,
            completed_tool_calls=0,
            started_at=datetime.utcnow(),
        )

        # Emit event
        await emitter.emit_swarm_created(swarm, session_id="test-session")

        await bridge.stop_swarm_emitter()

        # Check event was received
        assert len(received_events) == 1
        assert received_events[0].event_name == SwarmEventNames.SWARM_CREATED
        assert received_events[0].payload["swarm_id"] == "test-swarm"

    @pytest.mark.asyncio
    async def test_multiple_events_flow(self, bridge_config):
        """Test multiple events flow through."""
        received_events: List[CustomEvent] = []

        async def capture_callback(event: CustomEvent):
            received_events.append(event)

        bridge = HybridEventBridge(config=bridge_config)
        emitter = bridge.configure_swarm_emitter(event_callback=capture_callback)

        await bridge.start_swarm_emitter()

        # Create mock data
        from src.integrations.swarm.models import (
            AgentSwarmStatus,
            SwarmMode,
            SwarmStatus,
            WorkerExecution,
            WorkerType,
            WorkerStatus,
        )
        from datetime import datetime

        swarm = AgentSwarmStatus(
            swarm_id="test-swarm",
            mode=SwarmMode.SEQUENTIAL,
            status=SwarmStatus.RUNNING,
            overall_progress=0,
            workers=[],
            total_tool_calls=0,
            completed_tool_calls=0,
            started_at=datetime.utcnow(),
        )

        worker = WorkerExecution(
            worker_id="worker-1",
            worker_name="Test Agent",
            worker_type=WorkerType.CUSTOM,
            role="Worker",
            status=WorkerStatus.RUNNING,
            progress=0,
            started_at=datetime.utcnow(),
        )

        # Emit events
        await emitter.emit_swarm_created(swarm)
        await emitter.emit_worker_started("test-swarm", worker)

        # Mark completed
        worker.status = WorkerStatus.COMPLETED
        worker.completed_at = datetime.utcnow()
        await emitter.emit_worker_completed("test-swarm", worker)

        swarm.status = SwarmStatus.COMPLETED
        swarm.completed_at = datetime.utcnow()
        await emitter.emit_swarm_completed(swarm)

        await bridge.stop_swarm_emitter()

        # Check all events were received
        assert len(received_events) == 4

        event_names = [e.event_name for e in received_events]
        assert SwarmEventNames.SWARM_CREATED in event_names
        assert SwarmEventNames.WORKER_STARTED in event_names
        assert SwarmEventNames.WORKER_COMPLETED in event_names
        assert SwarmEventNames.SWARM_COMPLETED in event_names


class TestBridgeProperties:
    """Test bridge property access."""

    def test_swarm_emitter_property_none_before_configure(self):
        """Test that swarm_emitter is None before configuration."""
        bridge = HybridEventBridge()
        assert bridge.swarm_emitter is None

    def test_swarm_emitter_property_after_configure(self):
        """Test that swarm_emitter is accessible after configuration."""
        bridge = HybridEventBridge()
        bridge.configure_swarm_emitter()

        assert bridge.swarm_emitter is not None
        assert isinstance(bridge.swarm_emitter, SwarmEventEmitter)

    def test_existing_properties_still_work(self):
        """Test that existing bridge properties still work."""
        bridge = HybridEventBridge()

        assert bridge.orchestrator is None
        assert bridge.converters is not None
        assert bridge.config is not None
