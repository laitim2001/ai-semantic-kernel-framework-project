"""
Tests for Visualization API Endpoints

Sprint 38: 執行結果可視化
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.code_interpreter.visualization import (
    router,
    VisualizationRequest,
    VisualizationResponse,
    SUPPORTED_CHART_TYPES,
    _generate_chart_code,
)


# =============================================================================
# Test App Setup
# =============================================================================

app = FastAPI()
app.include_router(router, prefix="/code-interpreter")
client = TestClient(app)


# =============================================================================
# Chart Types Tests
# =============================================================================

class TestSupportedChartTypes:
    """測試支援的圖表類型。"""

    def test_supported_types_exist(self):
        """測試支援的類型存在。"""
        assert "bar" in SUPPORTED_CHART_TYPES
        assert "line" in SUPPORTED_CHART_TYPES
        assert "pie" in SUPPORTED_CHART_TYPES
        assert "scatter" in SUPPORTED_CHART_TYPES
        assert "hist" in SUPPORTED_CHART_TYPES
        assert "box" in SUPPORTED_CHART_TYPES

    def test_get_chart_types_endpoint(self):
        """測試獲取圖表類型端點。"""
        response = client.get("/code-interpreter/visualizations/types")

        assert response.status_code == 200
        data = response.json()
        assert "chart_types" in data
        assert "default" in data
        assert data["default"] == "bar"


# =============================================================================
# Generate Chart Code Tests
# =============================================================================

class TestGenerateChartCode:
    """測試圖表代碼生成。"""

    def test_generate_bar_chart(self):
        """測試生成柱狀圖代碼。"""
        code = _generate_chart_code(
            data={"A": 10, "B": 20},
            chart_type="bar",
            title="Test Bar",
        )

        assert "matplotlib" in code
        assert "bar" in code
        assert "Test Bar" in code
        assert "savefig" in code

    def test_generate_line_chart(self):
        """測試生成折線圖代碼。"""
        code = _generate_chart_code(
            data={"A": 10, "B": 20},
            chart_type="line",
            title="Test Line",
        )

        assert "plot" in code
        assert "marker" in code

    def test_generate_pie_chart(self):
        """測試生成圓餅圖代碼。"""
        code = _generate_chart_code(
            data={"A": 30, "B": 70},
            chart_type="pie",
        )

        assert "pie" in code
        assert "autopct" in code

    def test_generate_scatter_chart(self):
        """測試生成散點圖代碼。"""
        code = _generate_chart_code(
            data={"A": 10, "B": 20},
            chart_type="scatter",
        )

        assert "scatter" in code

    def test_generate_with_labels(self):
        """測試生成帶標籤的圖表。"""
        code = _generate_chart_code(
            data={"A": 10},
            chart_type="bar",
            title="My Chart",
            x_label="X Axis",
            y_label="Y Axis",
        )

        assert "My Chart" in code
        assert "X Axis" in code
        assert "Y Axis" in code

    def test_generate_with_custom_dimensions(self):
        """測試生成自定義尺寸的圖表。"""
        code = _generate_chart_code(
            data={"A": 10},
            chart_type="bar",
            width=12,
            height=8,
            dpi=200,
        )

        assert "12" in code
        assert "8" in code
        assert "200" in code


# =============================================================================
# Request/Response Schema Tests
# =============================================================================

class TestVisualizationRequest:
    """測試可視化請求 schema。"""

    def test_valid_request(self):
        """測試有效請求。"""
        request = VisualizationRequest(
            data={"A": 10, "B": 20},
            chart_type="bar",
            title="Test Chart",
        )

        assert request.data == {"A": 10, "B": 20}
        assert request.chart_type == "bar"
        assert request.title == "Test Chart"

    def test_default_values(self):
        """測試默認值。"""
        request = VisualizationRequest(data={"A": 1})

        assert request.chart_type == "bar"
        assert request.title is None
        assert request.width == 10
        assert request.height == 6
        assert request.dpi == 150

    def test_dimension_constraints(self):
        """測試尺寸約束。"""
        # Valid dimensions
        request = VisualizationRequest(
            data={"A": 1},
            width=4,
            height=3,
        )
        assert request.width == 4
        assert request.height == 3


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestGetVisualization:
    """測試獲取可視化端點。"""

    def test_get_visualization_success(self):
        """測試成功獲取可視化。"""
        with patch("src.api.v1.code_interpreter.visualization.get_file_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.download.return_value = b"PNG image content"
            mock_get_service.return_value = mock_service

            response = client.get("/code-interpreter/visualizations/file-123")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"

    def test_get_visualization_not_found(self):
        """測試獲取不存在的可視化。"""
        with patch("src.api.v1.code_interpreter.visualization.get_file_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.download.side_effect = Exception("File not found")
            mock_get_service.return_value = mock_service

            response = client.get("/code-interpreter/visualizations/nonexistent")

            assert response.status_code == 404

    def test_get_visualization_inline(self):
        """測試內聯顯示可視化。"""
        with patch("src.api.v1.code_interpreter.visualization.get_file_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.download.return_value = b"PNG"
            mock_get_service.return_value = mock_service

            response = client.get("/code-interpreter/visualizations/file-123?inline=true")

            assert response.status_code == 200
            assert "inline" in response.headers.get("content-disposition", "")

    def test_get_visualization_download(self):
        """測試下載可視化。"""
        with patch("src.api.v1.code_interpreter.visualization.get_file_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.download.return_value = b"PNG"
            mock_get_service.return_value = mock_service

            response = client.get("/code-interpreter/visualizations/file-123?inline=false")

            assert response.status_code == 200
            assert "attachment" in response.headers.get("content-disposition", "")


class TestGenerateVisualization:
    """測試生成可視化端點。"""

    @patch("src.api.v1.code_interpreter.visualization.CodeInterpreterAdapter")
    def test_generate_visualization_success(self, mock_adapter_class):
        """測試成功生成可視化。"""
        # Setup mock adapter
        mock_adapter = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Chart generated"
        mock_result.execution_time = 2.5
        mock_result.files = [
            {"type": "image", "file_id": "file-chart", "filename": "chart.png"}
        ]
        mock_result.error = None

        mock_adapter.execute.return_value = mock_result
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/visualizations/generate",
            json={
                "data": {"A": 10, "B": 20, "C": 30},
                "chart_type": "bar",
                "title": "Test Chart"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["chart_type"] == "bar"
        assert len(data["files"]) == 1

    def test_generate_visualization_invalid_chart_type(self):
        """測試生成無效圖表類型。"""
        response = client.post(
            "/code-interpreter/visualizations/generate",
            json={
                "data": {"A": 10},
                "chart_type": "invalid_type"
            }
        )

        assert response.status_code == 400
        assert "Unsupported chart type" in response.json()["detail"]

    def test_generate_visualization_missing_data(self):
        """測試生成缺少數據。"""
        response = client.post(
            "/code-interpreter/visualizations/generate",
            json={
                "chart_type": "bar"
            }
        )

        # Pydantic validation error
        assert response.status_code == 422

    @patch("src.api.v1.code_interpreter.visualization.CodeInterpreterAdapter")
    def test_generate_visualization_execution_error(self, mock_adapter_class):
        """測試生成執行錯誤。"""
        mock_adapter = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.output = ""
        mock_result.execution_time = 0.5
        mock_result.files = []
        mock_result.error = "Execution failed"

        mock_adapter.execute.return_value = mock_result
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/visualizations/generate",
            json={
                "data": {"A": 10},
                "chart_type": "bar"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Execution failed"


class TestVisualizationChartTypes:
    """測試各種圖表類型生成。"""

    @pytest.mark.parametrize("chart_type", [
        "bar", "barh", "line", "pie", "scatter", "hist", "box"
    ])
    @patch("src.api.v1.code_interpreter.visualization.CodeInterpreterAdapter")
    def test_all_chart_types(self, mock_adapter_class, chart_type):
        """測試所有支援的圖表類型。"""
        mock_adapter = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = f"{chart_type} chart generated"
        mock_result.execution_time = 1.0
        mock_result.files = []
        mock_result.error = None

        mock_adapter.execute.return_value = mock_result
        mock_adapter_class.return_value = mock_adapter

        response = client.post(
            "/code-interpreter/visualizations/generate",
            json={
                "data": {"A": 10, "B": 20},
                "chart_type": chart_type
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["chart_type"] == chart_type
