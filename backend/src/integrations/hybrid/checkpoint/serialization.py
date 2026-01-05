# =============================================================================
# IPA Platform - Checkpoint Serialization
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Serialization utilities for HybridCheckpoint with compression support.
# Provides efficient serialization/deserialization with integrity validation.
#
# Key Features:
#   - JSON serialization/deserialization
#   - Multiple compression algorithms (zlib, gzip)
#   - Checksum generation and validation
#   - Size optimization for large checkpoints
#
# Dependencies:
#   - HybridCheckpoint, CompressionAlgorithm (models)
# =============================================================================

import gzip
import hashlib
import json
import zlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .models import CompressionAlgorithm, HybridCheckpoint


# =============================================================================
# Serialization Configuration
# =============================================================================


@dataclass
class SerializationConfig:
    """
    Configuration for checkpoint serialization.

    Attributes:
        compression_algorithm: Algorithm to use for compression
        compression_level: Compression level (1-9, higher = better compression)
        compute_checksum: Whether to compute checksum
        min_size_for_compression: Minimum size in bytes to apply compression
        pretty_print: Whether to pretty-print JSON (for debugging)
    """

    compression_algorithm: CompressionAlgorithm = CompressionAlgorithm.ZLIB
    compression_level: int = 6
    compute_checksum: bool = True
    min_size_for_compression: int = 1024  # 1KB
    pretty_print: bool = False


# =============================================================================
# Serialization Result
# =============================================================================


@dataclass
class SerializationResult:
    """
    Result of a serialization operation.

    Attributes:
        data: Serialized bytes
        original_size: Original size before compression
        compressed_size: Size after compression (same as original if not compressed)
        compressed: Whether compression was applied
        algorithm: Compression algorithm used
        checksum: Data integrity checksum
        serialization_time_ms: Time taken for serialization
    """

    data: bytes
    original_size: int
    compressed_size: int
    compressed: bool
    algorithm: CompressionAlgorithm
    checksum: Optional[str]
    serialization_time_ms: int

    def get_compression_ratio(self) -> float:
        """Get compression ratio (0.0 = no compression, 1.0 = full compression)."""
        if self.original_size == 0:
            return 0.0
        return 1.0 - (self.compressed_size / self.original_size)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compressed": self.compressed,
            "algorithm": self.algorithm.value,
            "checksum": self.checksum,
            "compression_ratio": self.get_compression_ratio(),
            "serialization_time_ms": self.serialization_time_ms,
        }


@dataclass
class DeserializationResult:
    """
    Result of a deserialization operation.

    Attributes:
        checkpoint: Deserialized HybridCheckpoint
        was_compressed: Whether data was compressed
        checksum_valid: Whether checksum validation passed
        deserialization_time_ms: Time taken for deserialization
    """

    checkpoint: HybridCheckpoint
    was_compressed: bool
    checksum_valid: bool
    deserialization_time_ms: int


# =============================================================================
# Checkpoint Serializer
# =============================================================================


class CheckpointSerializer:
    """
    Serializer for HybridCheckpoint with compression support.

    Provides efficient serialization and deserialization of checkpoints
    with optional compression and integrity validation.

    Example:
        >>> serializer = CheckpointSerializer()
        >>> result = serializer.serialize(checkpoint)
        >>> print(f"Compression ratio: {result.get_compression_ratio():.2%}")

        >>> checkpoint = serializer.deserialize(result.data)
    """

    def __init__(self, config: Optional[SerializationConfig] = None):
        """
        Initialize serializer with configuration.

        Args:
            config: Serialization configuration. Uses defaults if not provided.
        """
        self.config = config or SerializationConfig()

    def serialize(self, checkpoint: HybridCheckpoint) -> SerializationResult:
        """
        Serialize a HybridCheckpoint to bytes.

        Args:
            checkpoint: Checkpoint to serialize

        Returns:
            SerializationResult with serialized data and metadata

        Example:
            >>> result = serializer.serialize(checkpoint)
            >>> with open("checkpoint.bin", "wb") as f:
            ...     f.write(result.data)
        """
        start_time = datetime.utcnow()

        # Convert to JSON
        checkpoint_dict = checkpoint.to_dict()
        if self.config.pretty_print:
            json_str = json.dumps(checkpoint_dict, indent=2, ensure_ascii=False)
        else:
            json_str = json.dumps(checkpoint_dict, separators=(",", ":"), ensure_ascii=False)

        json_bytes = json_str.encode("utf-8")
        original_size = len(json_bytes)

        # Decide whether to compress
        should_compress = (
            self.config.compression_algorithm != CompressionAlgorithm.NONE
            and original_size >= self.config.min_size_for_compression
        )

        if should_compress:
            compressed_bytes, algorithm = self._compress(
                json_bytes, self.config.compression_algorithm
            )
            final_bytes = compressed_bytes
            compressed = True
        else:
            final_bytes = json_bytes
            algorithm = CompressionAlgorithm.NONE
            compressed = False

        # Compute checksum
        checksum = None
        if self.config.compute_checksum:
            checksum = self._compute_checksum(final_bytes)

        # Update checkpoint metadata
        checkpoint.compressed = compressed
        checkpoint.compression_algorithm = algorithm
        checkpoint.checksum = checksum

        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return SerializationResult(
            data=final_bytes,
            original_size=original_size,
            compressed_size=len(final_bytes),
            compressed=compressed,
            algorithm=algorithm,
            checksum=checksum,
            serialization_time_ms=elapsed_ms,
        )

    def deserialize(
        self,
        data: bytes,
        expected_checksum: Optional[str] = None,
        compression_algorithm: Optional[CompressionAlgorithm] = None,
    ) -> DeserializationResult:
        """
        Deserialize bytes to a HybridCheckpoint.

        Args:
            data: Serialized checkpoint bytes
            expected_checksum: Expected checksum for validation (optional)
            compression_algorithm: Compression algorithm used (optional, auto-detected)

        Returns:
            DeserializationResult with deserialized checkpoint

        Raises:
            ValueError: If checksum validation fails
            json.JSONDecodeError: If data is not valid JSON

        Example:
            >>> with open("checkpoint.bin", "rb") as f:
            ...     data = f.read()
            >>> result = serializer.deserialize(data)
            >>> checkpoint = result.checkpoint
        """
        start_time = datetime.utcnow()

        # Validate checksum if provided
        checksum_valid = True
        if expected_checksum:
            actual_checksum = self._compute_checksum(data)
            checksum_valid = actual_checksum == expected_checksum
            if not checksum_valid:
                raise ValueError(
                    f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
                )

        # Decompress if needed
        was_compressed = False
        if compression_algorithm and compression_algorithm != CompressionAlgorithm.NONE:
            json_bytes = self._decompress(data, compression_algorithm)
            was_compressed = True
        else:
            # Try to detect compression
            json_bytes, detected_compressed = self._try_decompress(data)
            was_compressed = detected_compressed

        # Parse JSON
        json_str = json_bytes.decode("utf-8")
        checkpoint_dict = json.loads(json_str)

        # Create checkpoint
        checkpoint = HybridCheckpoint.from_dict(checkpoint_dict)

        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return DeserializationResult(
            checkpoint=checkpoint,
            was_compressed=was_compressed,
            checksum_valid=checksum_valid,
            deserialization_time_ms=elapsed_ms,
        )

    def serialize_to_json(self, checkpoint: HybridCheckpoint) -> str:
        """
        Serialize checkpoint to JSON string (no compression).

        Args:
            checkpoint: Checkpoint to serialize

        Returns:
            JSON string representation
        """
        checkpoint_dict = checkpoint.to_dict()
        return json.dumps(checkpoint_dict, indent=2, ensure_ascii=False)

    def deserialize_from_json(self, json_str: str) -> HybridCheckpoint:
        """
        Deserialize checkpoint from JSON string.

        Args:
            json_str: JSON string

        Returns:
            HybridCheckpoint instance
        """
        checkpoint_dict = json.loads(json_str)
        return HybridCheckpoint.from_dict(checkpoint_dict)

    # =========================================================================
    # Compression Methods
    # =========================================================================

    def _compress(
        self, data: bytes, algorithm: CompressionAlgorithm
    ) -> Tuple[bytes, CompressionAlgorithm]:
        """
        Compress data using specified algorithm.

        Args:
            data: Data to compress
            algorithm: Compression algorithm

        Returns:
            Tuple of (compressed_data, algorithm_used)
        """
        if algorithm == CompressionAlgorithm.ZLIB:
            compressed = zlib.compress(data, self.config.compression_level)
            return compressed, CompressionAlgorithm.ZLIB

        elif algorithm == CompressionAlgorithm.GZIP:
            compressed = gzip.compress(data, compresslevel=self.config.compression_level)
            return compressed, CompressionAlgorithm.GZIP

        elif algorithm == CompressionAlgorithm.LZ4:
            # LZ4 requires optional dependency
            try:
                import lz4.frame

                compressed = lz4.frame.compress(data)
                return compressed, CompressionAlgorithm.LZ4
            except ImportError:
                # Fall back to zlib if LZ4 not available
                compressed = zlib.compress(data, self.config.compression_level)
                return compressed, CompressionAlgorithm.ZLIB

        else:
            return data, CompressionAlgorithm.NONE

    def _decompress(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """
        Decompress data using specified algorithm.

        Args:
            data: Compressed data
            algorithm: Compression algorithm

        Returns:
            Decompressed data
        """
        if algorithm == CompressionAlgorithm.ZLIB:
            return zlib.decompress(data)

        elif algorithm == CompressionAlgorithm.GZIP:
            return gzip.decompress(data)

        elif algorithm == CompressionAlgorithm.LZ4:
            try:
                import lz4.frame

                return lz4.frame.decompress(data)
            except ImportError:
                raise ValueError("LZ4 decompression requires lz4 package")

        else:
            return data

    def _try_decompress(self, data: bytes) -> Tuple[bytes, bool]:
        """
        Try to decompress data, auto-detecting algorithm.

        Args:
            data: Potentially compressed data

        Returns:
            Tuple of (decompressed_data, was_compressed)
        """
        # Try zlib (starts with 0x78)
        if len(data) > 1 and data[0] == 0x78:
            try:
                return zlib.decompress(data), True
            except zlib.error:
                pass

        # Try gzip (starts with 0x1f 0x8b)
        if len(data) > 1 and data[0] == 0x1F and data[1] == 0x8B:
            try:
                return gzip.decompress(data), True
            except gzip.BadGzipFile:
                pass

        # Try LZ4 if available
        try:
            import lz4.frame

            try:
                return lz4.frame.decompress(data), True
            except Exception:
                pass
        except ImportError:
            pass

        # Not compressed or unknown format
        return data, False

    # =========================================================================
    # Checksum Methods
    # =========================================================================

    def _compute_checksum(self, data: bytes) -> str:
        """
        Compute SHA-256 checksum of data.

        Args:
            data: Data to checksum

        Returns:
            Hex string of checksum
        """
        return hashlib.sha256(data).hexdigest()

    def validate_checksum(self, data: bytes, expected_checksum: str) -> bool:
        """
        Validate data against expected checksum.

        Args:
            data: Data to validate
            expected_checksum: Expected checksum

        Returns:
            True if checksum matches
        """
        actual = self._compute_checksum(data)
        return actual == expected_checksum

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def estimate_compressed_size(self, checkpoint: HybridCheckpoint) -> int:
        """
        Estimate compressed size without actually compressing.

        Args:
            checkpoint: Checkpoint to estimate

        Returns:
            Estimated compressed size in bytes
        """
        # Quick estimate based on JSON size and typical compression ratio
        json_str = json.dumps(checkpoint.to_dict(), separators=(",", ":"))
        original_size = len(json_str.encode("utf-8"))

        # Typical compression ratios
        ratios = {
            CompressionAlgorithm.ZLIB: 0.4,  # ~60% reduction
            CompressionAlgorithm.GZIP: 0.4,
            CompressionAlgorithm.LZ4: 0.5,  # ~50% reduction
            CompressionAlgorithm.NONE: 1.0,
        }

        ratio = ratios.get(self.config.compression_algorithm, 0.5)
        return int(original_size * ratio)

    def get_size_info(self, checkpoint: HybridCheckpoint) -> Dict[str, Any]:
        """
        Get size information about a checkpoint.

        Args:
            checkpoint: Checkpoint to analyze

        Returns:
            Dictionary with size information
        """
        result = self.serialize(checkpoint)
        return {
            "original_size_bytes": result.original_size,
            "compressed_size_bytes": result.compressed_size,
            "compression_ratio": result.get_compression_ratio(),
            "algorithm": result.algorithm.value,
            "has_maf_state": checkpoint.has_maf_state(),
            "has_claude_state": checkpoint.has_claude_state(),
        }
