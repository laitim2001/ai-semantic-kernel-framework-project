"""
MAF ACL Adapter Tests

Tests MAFAdapter, exception wrapping, and MAFVersionDetector.

Sprint 128: Story 128-3
"""

import pytest
from unittest.mock import MagicMock, patch

from src.integrations.agent_framework.acl.adapter import (
    BUILDER_TYPE_MAP,
    MAFAdapter,
    get_maf_adapter,
    _maf_adapter_instance,
)
from src.integrations.agent_framework.acl.version_detector import (
    MAFVersionDetector,
    MAFVersionInfo,
)
from src.integrations.agent_framework.exceptions import (
    AdapterError,
    ExecutionError,
    WorkflowBuildError,
)


# =============================================================================
# MAFVersionDetector Tests
# =============================================================================


class TestMAFVersionDetector:
    """Tests for MAFVersionDetector."""

    def test_detect_with_agent_framework(self):
        """Detection succeeds when agent_framework is importable."""
        mock_module = MagicMock()
        mock_module.__version__ = "1.0.0b251204"

        with patch.dict("sys.modules", {"agent_framework": mock_module}):
            info = MAFVersionDetector.detect()

        assert info.is_available is True
        assert info.version == "1.0.0b251204"
        assert info.is_preview is True
        assert info.major == 1
        assert info.minor == 0
        assert info.patch == 0
        assert info.preview_tag == "b251204"
        assert info.api_compatibility == "full"

    def test_detect_without_agent_framework(self):
        """Detection handles ImportError gracefully."""
        with patch("builtins.__import__", side_effect=ImportError("not found")):
            info = MAFVersionDetector.detect()

        assert info.is_available is False
        assert info.api_compatibility == "unavailable"

    def test_detect_unknown_version(self):
        """Detection reports 'unknown' for unrecognized versions."""
        mock_module = MagicMock()
        mock_module.__version__ = "99.99.99"

        with patch.dict("sys.modules", {"agent_framework": mock_module}):
            info = MAFVersionDetector.detect()

        assert info.is_available is True
        assert info.api_compatibility == "unknown"

    def test_parse_version_standard(self):
        """Parse standard version string."""
        parsed = MAFVersionDetector._parse_version("1.2.3")
        assert parsed["major"] == 1
        assert parsed["minor"] == 2
        assert parsed["patch"] == 3
        assert parsed["is_preview"] is False

    def test_parse_version_preview(self):
        """Parse preview version string."""
        parsed = MAFVersionDetector._parse_version("1.0.0b251204")
        assert parsed["major"] == 1
        assert parsed["is_preview"] is True
        assert parsed["preview_tag"] == "b251204"

    def test_check_api_available(self):
        """check_api_available returns True for existing attributes."""
        import types

        mock_module = types.ModuleType("agent_framework")
        mock_module.__version__ = "1.0.0b251204"
        mock_module.GroupChatBuilder = MagicMock()

        with patch.dict("sys.modules", {"agent_framework": mock_module}):
            assert MAFVersionDetector.check_api_available("GroupChatBuilder") is True
            assert MAFVersionDetector.check_api_available("NonExistent") is False

    def test_is_compatible_full(self):
        """is_compatible returns True for 'full' compatibility."""
        info = MAFVersionInfo(is_available=True, api_compatibility="full")
        assert MAFVersionDetector.is_compatible(info) is True

    def test_is_compatible_partial(self):
        """is_compatible returns True for 'partial' compatibility."""
        info = MAFVersionInfo(is_available=True, api_compatibility="partial")
        assert MAFVersionDetector.is_compatible(info) is True

    def test_is_compatible_unavailable(self):
        """is_compatible returns False for 'unavailable'."""
        info = MAFVersionInfo(is_available=False, api_compatibility="unavailable")
        assert MAFVersionDetector.is_compatible(info) is False


# =============================================================================
# MAFAdapter Tests
# =============================================================================


class TestMAFAdapter:
    """Tests for MAFAdapter."""

    def test_create_builder_with_mocked_maf(self):
        """create_builder returns the MAF class for known types."""
        adapter = MAFAdapter()

        mock_module = MagicMock()
        mock_module.__version__ = "1.0.0b251204"
        mock_builder_cls = MagicMock()
        mock_module.GroupChatBuilder = mock_builder_cls

        with patch.dict("sys.modules", {"agent_framework": mock_module}):
            adapter.reset()
            result = adapter.create_builder("groupchat")

        assert result is mock_builder_cls

    def test_create_builder_unknown_type(self):
        """create_builder raises AdapterError for unknown types."""
        adapter = MAFAdapter()

        mock_module = MagicMock()
        mock_module.__version__ = "1.0.0b251204"

        with patch.dict("sys.modules", {"agent_framework": mock_module}):
            adapter.reset()
            with pytest.raises(AdapterError, match="Unknown builder type"):
                adapter.create_builder("nonexistent")

    def test_create_builder_maf_unavailable(self):
        """create_builder raises AdapterError when MAF is not available."""
        adapter = MAFAdapter()

        with patch("builtins.__import__", side_effect=ImportError("not found")):
            adapter.reset()
            with pytest.raises(AdapterError, match="not available"):
                adapter.create_builder("groupchat")

    def test_is_available(self):
        """is_available reflects detection result."""
        adapter = MAFAdapter()

        mock_module = MagicMock()
        mock_module.__version__ = "1.0.0b251204"

        with patch.dict("sys.modules", {"agent_framework": mock_module}):
            adapter.reset()
            assert adapter.is_available() is True

    def test_wrap_exception_build_error(self):
        """wrap_exception maps build-related errors to WorkflowBuildError."""
        adapter = MAFAdapter()
        error = Exception("build validation failed")

        wrapped = adapter.wrap_exception(error)
        assert isinstance(wrapped, WorkflowBuildError)

    def test_wrap_exception_runtime_error(self):
        """wrap_exception maps RuntimeError to ExecutionError."""
        adapter = MAFAdapter()
        error = RuntimeError("execution timeout")

        wrapped = adapter.wrap_exception(error)
        assert isinstance(wrapped, ExecutionError)

    def test_wrap_exception_generic(self):
        """wrap_exception wraps unknown errors as AdapterError."""
        adapter = MAFAdapter()
        error = ValueError("something unexpected")

        wrapped = adapter.wrap_exception(error)
        assert isinstance(wrapped, AdapterError)
        assert wrapped.original_error is error

    def test_reset_clears_state(self):
        """reset() clears detection cache."""
        adapter = MAFAdapter()
        adapter._detected = True
        adapter._version_info = MAFVersionInfo(is_available=True)

        adapter.reset()

        assert adapter._detected is False
        assert adapter._version_info is None


class TestGetMAFAdapterSingleton:
    """Tests for get_maf_adapter() singleton."""

    def test_returns_same_instance(self):
        """get_maf_adapter() returns the same instance each time."""
        import src.integrations.agent_framework.acl.adapter as adapter_module

        # Reset singleton
        adapter_module._maf_adapter_instance = None

        a1 = get_maf_adapter()
        a2 = get_maf_adapter()

        assert a1 is a2

        # Cleanup
        adapter_module._maf_adapter_instance = None
