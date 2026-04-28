# =============================================================================
# IPA Platform - Checkpoint Serialization Unit Tests
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Tests for CheckpointSerializer with compression and checksum validation.
# =============================================================================

import json

import pytest

from src.integrations.hybrid.checkpoint.models import (
    CheckpointType,
    ClaudeCheckpointState,
    CompressionAlgorithm,
    HybridCheckpoint,
    MAFCheckpointState,
)
from src.integrations.hybrid.checkpoint.serialization import (
    CheckpointSerializer,
    DeserializationResult,
    SerializationConfig,
    SerializationResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_checkpoint() -> HybridCheckpoint:
    """Create a simple checkpoint for testing."""
    return HybridCheckpoint(
        session_id="sess_123",
        execution_mode="chat",
    )


@pytest.fixture
def complex_checkpoint() -> HybridCheckpoint:
    """Create a complex checkpoint with both states."""
    maf_state = MAFCheckpointState(
        workflow_id="wf_123",
        workflow_name="Document Processing Workflow",
        current_step=3,
        total_steps=5,
        agent_states={
            "classifier": {"status": "completed", "output": "invoice"},
            "extractor": {"status": "running"},
        },
        variables={"document_id": "doc_456", "user_id": "user_789"},
        pending_approvals=["approval_1"],
        execution_log=[
            {"step": 1, "action": "classify", "result": "success"},
            {"step": 2, "action": "extract", "result": "success"},
        ],
    )

    claude_state = ClaudeCheckpointState(
        session_id="sess_123",
        conversation_history=[
            {"role": "user", "content": "Process this document"},
            {"role": "assistant", "content": "I'll analyze the document for you."},
            {"role": "user", "content": "Extract the invoice details"},
        ],
        tool_call_history=[
            {"tool": "classify_document", "result": "invoice"},
            {"tool": "extract_fields", "result": {"amount": 100.00}},
        ],
        context_variables={"document_type": "invoice"},
        active_hooks=["validation_hook", "audit_hook"],
    )

    return HybridCheckpoint(
        session_id="sess_123",
        checkpoint_type=CheckpointType.HITL,
        maf_state=maf_state,
        claude_state=claude_state,
        execution_mode="hybrid",
        sync_version=5,
    )


@pytest.fixture
def large_checkpoint() -> HybridCheckpoint:
    """Create a large checkpoint for compression testing."""
    # Create large conversation history
    conversation_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i} " * 100}
        for i in range(50)
    ]

    claude_state = ClaudeCheckpointState(
        session_id="sess_large",
        conversation_history=conversation_history,
    )

    return HybridCheckpoint(
        session_id="sess_large",
        claude_state=claude_state,
    )


@pytest.fixture
def serializer() -> CheckpointSerializer:
    """Create default serializer."""
    return CheckpointSerializer()


# =============================================================================
# SerializationConfig Tests
# =============================================================================


class TestSerializationConfig:
    """Tests for SerializationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SerializationConfig()

        assert config.compression_algorithm == CompressionAlgorithm.ZLIB
        assert config.compression_level == 6
        assert config.compute_checksum is True
        assert config.min_size_for_compression == 1024
        assert config.pretty_print is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = SerializationConfig(
            compression_algorithm=CompressionAlgorithm.GZIP,
            compression_level=9,
            compute_checksum=False,
            min_size_for_compression=512,
            pretty_print=True,
        )

        assert config.compression_algorithm == CompressionAlgorithm.GZIP
        assert config.compression_level == 9
        assert config.compute_checksum is False
        assert config.min_size_for_compression == 512
        assert config.pretty_print is True


# =============================================================================
# Basic Serialization Tests
# =============================================================================


class TestBasicSerialization:
    """Tests for basic serialization operations."""

    def test_serialize_simple_checkpoint(self, serializer, simple_checkpoint):
        """Test serializing a simple checkpoint."""
        result = serializer.serialize(simple_checkpoint)

        assert isinstance(result, SerializationResult)
        assert isinstance(result.data, bytes)
        assert result.original_size > 0
        assert result.checksum is not None

    def test_serialize_complex_checkpoint(self, serializer, complex_checkpoint):
        """Test serializing a complex checkpoint."""
        result = serializer.serialize(complex_checkpoint)

        assert result.original_size > 500  # Should be larger
        assert result.checksum is not None

    def test_deserialize_simple_checkpoint(self, serializer, simple_checkpoint):
        """Test deserializing a simple checkpoint."""
        serialized = serializer.serialize(simple_checkpoint)
        result = serializer.deserialize(
            serialized.data,
            expected_checksum=serialized.checksum,
            compression_algorithm=serialized.algorithm,
        )

        assert isinstance(result, DeserializationResult)
        assert result.checkpoint.session_id == simple_checkpoint.session_id
        assert result.checksum_valid is True

    def test_serialize_deserialize_roundtrip(self, serializer, complex_checkpoint):
        """Test full serialization/deserialization roundtrip."""
        serialized = serializer.serialize(complex_checkpoint)
        result = serializer.deserialize(
            serialized.data,
            expected_checksum=serialized.checksum,
            compression_algorithm=serialized.algorithm,
        )

        restored = result.checkpoint

        assert restored.session_id == complex_checkpoint.session_id
        assert restored.checkpoint_type == complex_checkpoint.checkpoint_type
        assert restored.execution_mode == complex_checkpoint.execution_mode
        assert restored.maf_state.workflow_id == complex_checkpoint.maf_state.workflow_id
        assert (
            restored.claude_state.get_message_count()
            == complex_checkpoint.claude_state.get_message_count()
        )


# =============================================================================
# Compression Tests
# =============================================================================


class TestCompression:
    """Tests for compression functionality."""

    def test_small_data_not_compressed(self, simple_checkpoint):
        """Test that small data is not compressed."""
        config = SerializationConfig(min_size_for_compression=10000)
        serializer = CheckpointSerializer(config)

        result = serializer.serialize(simple_checkpoint)

        assert not result.compressed
        assert result.algorithm == CompressionAlgorithm.NONE
        assert result.original_size == result.compressed_size

    def test_large_data_compressed_zlib(self, large_checkpoint):
        """Test that large data is compressed with zlib."""
        config = SerializationConfig(
            compression_algorithm=CompressionAlgorithm.ZLIB,
            min_size_for_compression=100,
        )
        serializer = CheckpointSerializer(config)

        result = serializer.serialize(large_checkpoint)

        assert result.compressed
        assert result.algorithm == CompressionAlgorithm.ZLIB
        assert result.compressed_size < result.original_size
        assert result.get_compression_ratio() > 0

    def test_large_data_compressed_gzip(self, large_checkpoint):
        """Test that large data is compressed with gzip."""
        config = SerializationConfig(
            compression_algorithm=CompressionAlgorithm.GZIP,
            min_size_for_compression=100,
        )
        serializer = CheckpointSerializer(config)

        result = serializer.serialize(large_checkpoint)

        assert result.compressed
        assert result.algorithm == CompressionAlgorithm.GZIP
        assert result.compressed_size < result.original_size

    def test_no_compression(self, large_checkpoint):
        """Test disabling compression."""
        config = SerializationConfig(compression_algorithm=CompressionAlgorithm.NONE)
        serializer = CheckpointSerializer(config)

        result = serializer.serialize(large_checkpoint)

        assert not result.compressed
        assert result.algorithm == CompressionAlgorithm.NONE
        assert result.original_size == result.compressed_size

    def test_compressed_deserialize(self, large_checkpoint):
        """Test deserializing compressed data."""
        config = SerializationConfig(
            compression_algorithm=CompressionAlgorithm.ZLIB,
            min_size_for_compression=100,
        )
        serializer = CheckpointSerializer(config)

        serialized = serializer.serialize(large_checkpoint)
        result = serializer.deserialize(
            serialized.data,
            compression_algorithm=serialized.algorithm,
        )

        assert result.was_compressed is True
        assert result.checkpoint.session_id == large_checkpoint.session_id

    def test_auto_detect_compression(self, large_checkpoint):
        """Test auto-detecting compression algorithm."""
        config = SerializationConfig(
            compression_algorithm=CompressionAlgorithm.ZLIB,
            min_size_for_compression=100,
        )
        serializer = CheckpointSerializer(config)

        serialized = serializer.serialize(large_checkpoint)

        # Deserialize without specifying algorithm
        result = serializer.deserialize(serialized.data)

        assert result.was_compressed is True
        assert result.checkpoint.session_id == large_checkpoint.session_id

    def test_compression_ratio(self, large_checkpoint):
        """Test compression ratio calculation."""
        config = SerializationConfig(
            compression_algorithm=CompressionAlgorithm.ZLIB,
            min_size_for_compression=100,
        )
        serializer = CheckpointSerializer(config)

        result = serializer.serialize(large_checkpoint)

        ratio = result.get_compression_ratio()
        assert 0 < ratio < 1  # Should have some compression
        assert ratio > 0.3  # Text data should compress well


# =============================================================================
# Checksum Tests
# =============================================================================


class TestChecksum:
    """Tests for checksum functionality."""

    def test_checksum_computed(self, serializer, simple_checkpoint):
        """Test that checksum is computed."""
        result = serializer.serialize(simple_checkpoint)

        assert result.checksum is not None
        assert len(result.checksum) == 64  # SHA-256 hex

    def test_checksum_disabled(self, simple_checkpoint):
        """Test disabling checksum computation."""
        config = SerializationConfig(compute_checksum=False)
        serializer = CheckpointSerializer(config)

        result = serializer.serialize(simple_checkpoint)

        assert result.checksum is None

    def test_checksum_validation_success(self, serializer, simple_checkpoint):
        """Test successful checksum validation."""
        serialized = serializer.serialize(simple_checkpoint)

        result = serializer.deserialize(
            serialized.data,
            expected_checksum=serialized.checksum,
        )

        assert result.checksum_valid is True

    def test_checksum_validation_failure(self, serializer, simple_checkpoint):
        """Test failed checksum validation."""
        serialized = serializer.serialize(simple_checkpoint)

        with pytest.raises(ValueError, match="Checksum mismatch"):
            serializer.deserialize(
                serialized.data,
                expected_checksum="invalid_checksum",
            )

    def test_validate_checksum_method(self, serializer, simple_checkpoint):
        """Test validate_checksum method."""
        serialized = serializer.serialize(simple_checkpoint)

        assert serializer.validate_checksum(serialized.data, serialized.checksum)
        assert not serializer.validate_checksum(serialized.data, "wrong_checksum")


# =============================================================================
# JSON Serialization Tests
# =============================================================================


class TestJsonSerialization:
    """Tests for JSON serialization methods."""

    def test_serialize_to_json(self, serializer, complex_checkpoint):
        """Test serializing to JSON string."""
        json_str = serializer.serialize_to_json(complex_checkpoint)

        assert isinstance(json_str, str)

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["session_id"] == complex_checkpoint.session_id

    def test_deserialize_from_json(self, serializer, complex_checkpoint):
        """Test deserializing from JSON string."""
        json_str = serializer.serialize_to_json(complex_checkpoint)
        restored = serializer.deserialize_from_json(json_str)

        assert restored.session_id == complex_checkpoint.session_id
        assert restored.checkpoint_type == complex_checkpoint.checkpoint_type


# =============================================================================
# Utility Method Tests
# =============================================================================


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_estimate_compressed_size(self, serializer, large_checkpoint):
        """Test compressed size estimation."""
        estimated = serializer.estimate_compressed_size(large_checkpoint)

        # Actually serialize and compare
        result = serializer.serialize(large_checkpoint)

        # Estimate should return a positive number
        # Note: For highly repetitive data, actual compression can be much better
        # than the generic estimation, so we just verify the estimate is reasonable
        assert estimated > 0
        # Estimate is based on 40% of original size for zlib
        # It should be less than original but more than 0
        assert estimated < result.original_size
        # The estimate should be in a reasonable range relative to original
        estimate_ratio = estimated / result.original_size
        assert 0.3 <= estimate_ratio <= 0.6  # Expected ~0.4 for zlib

    def test_get_size_info(self, serializer, complex_checkpoint):
        """Test getting size information."""
        info = serializer.get_size_info(complex_checkpoint)

        assert "original_size_bytes" in info
        assert "compressed_size_bytes" in info
        assert "compression_ratio" in info
        assert "algorithm" in info
        assert "has_maf_state" in info
        assert "has_claude_state" in info

        assert info["has_maf_state"] is True
        assert info["has_claude_state"] is True


# =============================================================================
# SerializationResult Tests
# =============================================================================


class TestSerializationResult:
    """Tests for SerializationResult."""

    def test_to_dict(self, serializer, simple_checkpoint):
        """Test result to_dict method."""
        result = serializer.serialize(simple_checkpoint)
        data = result.to_dict()

        assert "original_size" in data
        assert "compressed_size" in data
        assert "compressed" in data
        assert "algorithm" in data
        assert "checksum" in data
        assert "compression_ratio" in data
        assert "serialization_time_ms" in data

    def test_compression_ratio_no_compression(self):
        """Test compression ratio with no compression."""
        result = SerializationResult(
            data=b"test",
            original_size=100,
            compressed_size=100,
            compressed=False,
            algorithm=CompressionAlgorithm.NONE,
            checksum=None,
            serialization_time_ms=10,
        )

        assert result.get_compression_ratio() == 0.0

    def test_compression_ratio_with_compression(self):
        """Test compression ratio with compression."""
        result = SerializationResult(
            data=b"test",
            original_size=100,
            compressed_size=50,
            compressed=True,
            algorithm=CompressionAlgorithm.ZLIB,
            checksum="abc",
            serialization_time_ms=10,
        )

        assert result.get_compression_ratio() == 0.5

    def test_compression_ratio_zero_size(self):
        """Test compression ratio with zero original size."""
        result = SerializationResult(
            data=b"",
            original_size=0,
            compressed_size=0,
            compressed=False,
            algorithm=CompressionAlgorithm.NONE,
            checksum=None,
            serialization_time_ms=0,
        )

        assert result.get_compression_ratio() == 0.0


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_checkpoint(self, serializer):
        """Test serializing empty checkpoint."""
        checkpoint = HybridCheckpoint()
        result = serializer.serialize(checkpoint)

        assert result.data
        assert result.original_size > 0

    def test_checkpoint_with_unicode(self, serializer):
        """Test serializing checkpoint with unicode content."""
        claude_state = ClaudeCheckpointState(
            session_id="sess_unicode",
            conversation_history=[
                {"role": "user", "content": "你好世界 Hello World 🌍"},
                {"role": "assistant", "content": "日本語テスト 한국어테스트"},
            ],
        )

        checkpoint = HybridCheckpoint(
            session_id="sess_unicode",
            claude_state=claude_state,
        )

        serialized = serializer.serialize(checkpoint)
        result = serializer.deserialize(
            serialized.data,
            compression_algorithm=serialized.algorithm,
        )

        assert result.checkpoint.claude_state.conversation_history[0]["content"] == "你好世界 Hello World 🌍"

    def test_checkpoint_with_nested_data(self, serializer):
        """Test serializing checkpoint with deeply nested data."""
        nested_data = {"level1": {"level2": {"level3": {"level4": "deep_value"}}}}

        maf_state = MAFCheckpointState(
            workflow_id="wf_nested",
            workflow_name="Nested Test",
            variables=nested_data,
        )

        checkpoint = HybridCheckpoint(
            session_id="sess_nested",
            maf_state=maf_state,
        )

        serialized = serializer.serialize(checkpoint)
        result = serializer.deserialize(
            serialized.data,
            compression_algorithm=serialized.algorithm,
        )

        assert (
            result.checkpoint.maf_state.variables["level1"]["level2"]["level3"]["level4"]
            == "deep_value"
        )

    def test_pretty_print_config(self, simple_checkpoint):
        """Test pretty print configuration."""
        config = SerializationConfig(
            pretty_print=True,
            compression_algorithm=CompressionAlgorithm.NONE,
        )
        serializer = CheckpointSerializer(config)

        result = serializer.serialize(simple_checkpoint)

        # Pretty printed JSON should contain newlines
        json_str = result.data.decode("utf-8")
        assert "\n" in json_str
        assert "  " in json_str  # Indentation
