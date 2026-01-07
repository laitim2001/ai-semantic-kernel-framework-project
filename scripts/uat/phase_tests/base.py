"""
Phase Tests Base Class

提供 Phase 測試的共用基礎類和工具函數。
"""

import asyncio
import json
import logging
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import httpx

# Support both module and script execution
try:
    from .config import PhaseTestConfig, DEFAULT_CONFIG
except ImportError:
    from config import PhaseTestConfig, DEFAULT_CONFIG


def safe_print(text: str):
    """安全列印，處理編碼問題"""
    try:
        print(text)
    except UnicodeEncodeError:
        replacements = {
            '✅': '[PASS]',
            '❌': '[FAIL]',
            '⏭️': '[SKIP]',
            '💥': '[ERROR]',
            '🔄': '[RUN]',
            '📊': '[DATA]',
            '🤖': '[AI]',
            '📁': '[FILE]',
            '🔧': '[TOOL]',
            '💬': '[MSG]',
        }
        safe_text = text
        for char, replacement in replacements.items():
            safe_text = safe_text.replace(char, replacement)
        print(safe_text.encode('ascii', 'replace').decode('ascii'))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class TestStatus(Enum):
    """測試狀態"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestPhase(Enum):
    """測試階段"""
    PHASE_8 = "phase_8_code_interpreter"
    PHASE_9 = "phase_9_mcp_architecture"
    PHASE_10 = "phase_10_session_mode"
    PHASE_11 = "phase_11_agent_session_integration"
    PHASE_12 = "phase_12_claude_agent_sdk"
    PHASE_13 = "phase_13_hybrid_core"
    PHASE_14 = "phase_14_advanced_hybrid"
    PHASE_15 = "phase_15_ag_ui_protocol"
    PHASE_16 = "phase_16_unified_chat"


@dataclass
class StepResult:
    """單一步驟的測試結果"""
    step_id: str
    step_name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ai_response: Optional[str] = None  # 真實 AI 回應
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "details": self.details,
            "ai_response": self.ai_response,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ScenarioResult:
    """場景測試結果"""
    scenario_id: str
    scenario_name: str
    phase: TestPhase
    status: TestStatus
    total_steps: int
    passed: int
    failed: int
    skipped: int
    duration_ms: float
    step_results: List[StepResult] = field(default_factory=list)
    summary: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "phase": self.phase.value,
            "status": self.status.value,
            "total_steps": self.total_steps,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "step_results": [r.to_dict() for r in self.step_results],
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }


class PhaseTestBase(ABC):
    """
    Phase 測試基礎類

    所有 Phase 測試場景都應繼承此類並實現必要的方法。
    """

    # 子類需要覆蓋的屬性
    SCENARIO_ID: str = ""
    SCENARIO_NAME: str = ""
    SCENARIO_DESCRIPTION: str = ""
    PHASE: TestPhase = TestPhase.PHASE_8

    def __init__(self, config: Optional[PhaseTestConfig] = None):
        """
        初始化測試

        Args:
            config: 測試配置，若為 None 則使用預設配置
        """
        self.config = config or DEFAULT_CONFIG
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client: Optional[httpx.AsyncClient] = None
        self.step_results: List[StepResult] = []
        self.start_time: Optional[float] = None

        # LLM Service (延遲載入)
        self._llm_service = None

    async def __aenter__(self):
        """非同步上下文管理器進入"""
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同步上下文管理器退出"""
        if self.client:
            await self.client.aclose()

    @property
    def llm_service(self):
        """延遲載入 LLM Service"""
        if self._llm_service is None and self.config.use_real_llm:
            try:
                # 動態載入以避免循環依賴
                backend_path = str(Path(__file__).parent.parent.parent.parent / "backend")
                if backend_path not in sys.path:
                    sys.path.insert(0, backend_path)

                from src.integrations.llm import LLMServiceFactory
                self._llm_service = LLMServiceFactory.create(self.config.llm_provider)
                self.logger.info(f"LLM Service loaded: {self.config.llm_provider}")
            except ImportError as e:
                self.logger.warning(f"Failed to load LLM Service: {e}")
                self._llm_service = None
        return self._llm_service

    # =========================================================================
    # HTTP 請求方法
    # =========================================================================

    async def api_get(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> httpx.Response:
        """GET 請求"""
        return await self.client.get(endpoint, params=params)

    async def api_post(
        self,
        endpoint: str,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> httpx.Response:
        """POST 請求"""
        if files:
            return await self.client.post(endpoint, files=files)
        return await self.client.post(endpoint, json=json_data)

    async def api_delete(self, endpoint: str) -> httpx.Response:
        """DELETE 請求"""
        return await self.client.delete(endpoint)

    # =========================================================================
    # 測試步驟執行
    # =========================================================================

    async def run_step(
        self,
        step_id: str,
        step_name: str,
        step_func: Callable,
        *args,
        **kwargs
    ) -> StepResult:
        """
        執行單一測試步驟

        Args:
            step_id: 步驟 ID
            step_name: 步驟名稱
            step_func: 步驟執行函數
            *args, **kwargs: 傳遞給步驟函數的參數

        Returns:
            StepResult: 步驟執行結果
        """
        safe_print(f"\n🔄 Step {step_id}: {step_name}")
        start_time = time.time()

        try:
            result = await step_func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # 判斷結果類型
            if isinstance(result, dict):
                status = TestStatus.PASSED if result.get("success", True) else TestStatus.FAILED
                message = result.get("message", "")
                details = result.get("details", {})
                ai_response = result.get("ai_response")
            else:
                status = TestStatus.PASSED
                message = str(result) if result else "Step completed"
                details = {}
                ai_response = None

            step_result = StepResult(
                step_id=step_id,
                step_name=step_name,
                status=status,
                duration_ms=duration_ms,
                message=message,
                details=details,
                ai_response=ai_response
            )

            status_icon = "✅" if status == TestStatus.PASSED else "❌"
            safe_print(f"   {status_icon} {message} ({duration_ms:.1f}ms)")

            if ai_response:
                # 顯示 AI 回應摘要
                ai_summary = ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
                safe_print(f"   🤖 AI Response: {ai_summary}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            step_result = StepResult(
                step_id=step_id,
                step_name=step_name,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                message=f"Error: {str(e)}",
                details={"error_type": type(e).__name__}
            )
            safe_print(f"   💥 Error: {e}")

        self.step_results.append(step_result)
        return step_result

    # =========================================================================
    # 場景執行和報告
    # =========================================================================

    @abstractmethod
    async def setup(self) -> bool:
        """場景初始化，子類必須實現"""
        pass

    @abstractmethod
    async def execute(self) -> bool:
        """場景執行，子類必須實現"""
        pass

    @abstractmethod
    async def teardown(self) -> bool:
        """場景清理，子類必須實現"""
        pass

    async def run(self) -> ScenarioResult:
        """
        執行完整測試場景

        Returns:
            ScenarioResult: 場景執行結果
        """
        self.start_time = time.time()
        self.step_results = []

        safe_print("\n" + "=" * 70)
        safe_print(f"🧪 Phase Test: {self.SCENARIO_NAME}")
        safe_print(f"   Phase: {self.PHASE.value}")
        safe_print(f"   Description: {self.SCENARIO_DESCRIPTION}")
        safe_print("=" * 70)

        async with self:
            try:
                # Setup
                safe_print("\n--- Setup ---")
                setup_ok = await self.setup()
                if not setup_ok:
                    safe_print("❌ Setup failed, aborting test")
                    return self._build_result(TestStatus.ERROR)

                # Execute
                safe_print("\n--- Execute ---")
                execute_ok = await self.execute()

                # Teardown
                safe_print("\n--- Teardown ---")
                await self.teardown()

                # Build result
                status = TestStatus.PASSED if execute_ok else TestStatus.FAILED
                return self._build_result(status)

            except Exception as e:
                safe_print(f"\n💥 Scenario Error: {e}")
                await self.teardown()
                return self._build_result(TestStatus.ERROR)

    def _build_result(self, status: TestStatus) -> ScenarioResult:
        """構建場景結果"""
        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else 0

        passed = sum(1 for r in self.step_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.step_results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.step_results if r.status == TestStatus.SKIPPED)

        result = ScenarioResult(
            scenario_id=self.SCENARIO_ID,
            scenario_name=self.SCENARIO_NAME,
            phase=self.PHASE,
            status=status,
            total_steps=len(self.step_results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=duration_ms,
            step_results=self.step_results,
            summary=f"Passed: {passed}, Failed: {failed}, Skipped: {skipped}"
        )

        # Print summary
        safe_print("\n" + "=" * 70)
        safe_print(f"📊 Result: {status.value.upper()}")
        safe_print(f"   Total Steps: {result.total_steps}")
        safe_print(f"   ✅ Passed: {passed}")
        safe_print(f"   ❌ Failed: {failed}")
        safe_print(f"   ⏭️ Skipped: {skipped}")
        safe_print(f"   Duration: {duration_ms:.1f}ms")
        safe_print("=" * 70)

        return result

    def save_results(self, output_path: Optional[Path] = None) -> Path:
        """
        保存測試結果到 JSON 文件

        Args:
            output_path: 輸出路徑，若為 None 則使用預設路徑

        Returns:
            Path: 結果文件路徑
        """
        if output_path is None:
            output_path = self.config.output_dir / self.PHASE.value / "test_results.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 讀取現有結果
        existing_results = []
        if output_path.exists():
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_results = json.load(f)
                    if not isinstance(existing_results, list):
                        existing_results = [existing_results]
            except:
                pass

        # 添加當前結果
        result = self._build_result(
            TestStatus.PASSED if all(
                r.status == TestStatus.PASSED for r in self.step_results
            ) else TestStatus.FAILED
        )
        existing_results.append(result.to_dict())

        # 保存
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing_results, f, indent=2, ensure_ascii=False)

        safe_print(f"\n📁 Results saved to: {output_path}")
        return output_path


# =========================================================================
# 工具函數
# =========================================================================

def create_test_data_csv(data: List[Dict], filename: str = "test_data.csv") -> Path:
    """創建測試用 CSV 文件"""
    import csv
    from tempfile import gettempdir

    path = Path(gettempdir()) / filename

    if data:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    return path


def create_test_log_file(content: str, filename: str = "test_log.txt") -> Path:
    """創建測試用日誌文件"""
    from tempfile import gettempdir

    path = Path(gettempdir()) / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return path
