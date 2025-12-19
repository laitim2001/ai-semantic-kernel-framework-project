# =============================================================================
# UAT Scenario Test Base Class
# =============================================================================
# 所有場景測試的基礎類，提供通用的測試功能和報告生成。
#
# Author: IPA Platform Team
# Version: 1.0.0
# Created: 2025-12-18
# =============================================================================

"""
Base class for UAT scenario tests.
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
from typing import Any, Dict, List, Optional

import httpx


def safe_print(text: str):
    """Print text with fallback for encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic characters with ASCII alternatives
        replacements = {
            '✅': '[PASS]',
            '❌': '[FAIL]',
            '⏭️': '[SKIP]',
            '💥': '[ERROR]',
            '❓': '[?]',
        }
        safe_text = text
        for char, replacement in replacements.items():
            safe_text = safe_text.replace(char, replacement)
        # Encode to ASCII with replace for any remaining issues
        print(safe_text.encode('ascii', 'replace').decode('ascii'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single test case."""
    test_id: str
    test_name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ScenarioResult:
    """Result of a complete scenario test."""
    scenario_id: str
    scenario_name: str
    status: TestStatus
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_ms: float
    test_results: List[TestResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "status": self.status.value,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "test_results": [r.to_dict() for r in self.test_results],
            "timestamp": self.timestamp.isoformat(),
        }


class ScenarioTestBase(ABC):
    """
    Base class for scenario tests.

    All scenario test classes should inherit from this class and implement
    the required abstract methods.
    """

    # Class attributes to be overridden by subclasses
    SCENARIO_ID: str = ""
    SCENARIO_NAME: str = ""
    SCENARIO_DESCRIPTION: str = ""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        verbose: bool = True,
    ):
        """
        Initialize the scenario test.

        Args:
            base_url: Base URL of the API server
            timeout: Request timeout in seconds
            verbose: Whether to print verbose output
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_results: List[TestResult] = []
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    def _normalize_endpoint(self, endpoint: str) -> str:
        """
        Normalize API endpoint to match FastAPI route definitions.

        Collection endpoints (e.g., /api/v1/agents) need trailing slashes
        because FastAPI routes are defined with trailing slashes.
        Resource endpoints with IDs (e.g., /api/v1/agents/{id}) don't need them.

        Args:
            endpoint: The API endpoint path

        Returns:
            Normalized endpoint with appropriate trailing slash
        """
        # Don't modify health and root endpoints
        if endpoint in ["/", "/health", "/ready"]:
            return endpoint

        # Check if endpoint ends with an ID pattern (UUID or similar)
        # or has a specific action at the end
        parts = endpoint.rstrip("/").split("/")
        last_part = parts[-1] if parts else ""

        # If last part looks like an ID (UUID, number, or specific action keywords)
        # don't add trailing slash
        action_keywords = ["start", "stop", "execute", "trigger", "approve",
                          "reject", "cancel", "match", "calculate", "close",
                          "terminate", "run", "history", "pending", "stats",
                          "statistics", "summary", "transcript", "status"]

        # Check if it's a resource path (has ID-like segment or action)
        if (len(last_part) >= 8 and "-" in last_part) or \
           last_part.isdigit() or \
           last_part in action_keywords:
            return endpoint.rstrip("/")

        # For collection endpoints, ensure trailing slash
        if not endpoint.endswith("/"):
            return endpoint + "/"

        return endpoint

    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # -------------------------------------------------------------------------
    # Abstract methods to be implemented by subclasses
    # -------------------------------------------------------------------------

    @abstractmethod
    async def setup(self) -> bool:
        """
        Setup before running tests.

        Returns:
            True if setup successful, False otherwise
        """
        pass

    @abstractmethod
    async def teardown(self) -> bool:
        """
        Cleanup after running tests.

        Returns:
            True if teardown successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_test_cases(self) -> List[Dict[str, Any]]:
        """
        Get list of test cases to run.

        Returns:
            List of test case definitions
        """
        pass

    @abstractmethod
    async def run_test_case(self, test_case: Dict[str, Any]) -> TestResult:
        """
        Run a single test case.

        Args:
            test_case: Test case definition

        Returns:
            TestResult object
        """
        pass

    # -------------------------------------------------------------------------
    # Common test utilities
    # -------------------------------------------------------------------------

    async def api_get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make GET request to API."""
        normalized = self._normalize_endpoint(endpoint)
        return await self.client.get(normalized, params=params)

    async def api_post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make POST request to API."""
        normalized = self._normalize_endpoint(endpoint)
        return await self.client.post(normalized, data=data, json=json_data)

    async def api_put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Make PUT request to API."""
        normalized = self._normalize_endpoint(endpoint)
        return await self.client.put(normalized, json=json_data)

    async def api_delete(self, endpoint: str) -> httpx.Response:
        """Make DELETE request to API."""
        normalized = self._normalize_endpoint(endpoint)
        return await self.client.delete(normalized)

    async def check_health(self) -> bool:
        """Check if API server is healthy."""
        try:
            response = await self.api_get("/health")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    async def wait_for_condition(
        self,
        check_func,
        timeout: float = 30.0,
        interval: float = 1.0,
        description: str = "condition",
    ) -> bool:
        """
        Wait for a condition to be true.

        Args:
            check_func: Async function that returns True when condition is met
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds
            description: Description of what we're waiting for

        Returns:
            True if condition met, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if await check_func():
                    return True
            except Exception as e:
                self.logger.debug(f"Check failed: {e}")
            await asyncio.sleep(interval)

        self.logger.warning(f"Timeout waiting for {description}")
        return False

    def create_test_result(
        self,
        test_id: str,
        test_name: str,
        status: TestStatus,
        duration_ms: float,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> TestResult:
        """Create a TestResult object."""
        return TestResult(
            test_id=test_id,
            test_name=test_name,
            status=status,
            duration_ms=duration_ms,
            message=message,
            details=details or {},
        )

    # -------------------------------------------------------------------------
    # Test execution
    # -------------------------------------------------------------------------

    async def run(self) -> ScenarioResult:
        """
        Run all tests in the scenario.

        Returns:
            ScenarioResult object with all test results
        """
        scenario_start = time.time()
        self.test_results = []

        self.log_header()

        # Setup
        self.log_info("Setting up scenario...")
        try:
            setup_ok = await self.setup()
            if not setup_ok:
                return self._create_error_result("Setup failed")
        except Exception as e:
            self.logger.error(f"Setup error: {e}")
            return self._create_error_result(f"Setup error: {e}")

        # Get test cases
        try:
            test_cases = await self.get_test_cases()
            self.log_info(f"Found {len(test_cases)} test cases")
        except Exception as e:
            self.logger.error(f"Failed to get test cases: {e}")
            return self._create_error_result(f"Failed to get test cases: {e}")

        # Run tests
        for i, test_case in enumerate(test_cases, 1):
            test_id = test_case.get("id", f"TC-{i:03d}")
            test_name = test_case.get("name", f"Test {i}")

            self.log_info(f"Running [{i}/{len(test_cases)}]: {test_name}")

            try:
                result = await self.run_test_case(test_case)
                self.test_results.append(result)
                self._log_test_result(result)
            except Exception as e:
                self.logger.error(f"Test error: {e}")
                error_result = self.create_test_result(
                    test_id=test_id,
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    duration_ms=0,
                    message=str(e),
                )
                self.test_results.append(error_result)

        # Teardown
        self.log_info("Cleaning up scenario...")
        try:
            await self.teardown()
        except Exception as e:
            self.logger.warning(f"Teardown error: {e}")

        # Close client
        await self.close()

        # Create scenario result
        scenario_duration = (time.time() - scenario_start) * 1000
        return self._create_scenario_result(scenario_duration)

    def _create_scenario_result(self, duration_ms: float) -> ScenarioResult:
        """Create ScenarioResult from test results."""
        passed = sum(1 for r in self.test_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.test_results if r.status in [TestStatus.FAILED, TestStatus.ERROR])
        skipped = sum(1 for r in self.test_results if r.status == TestStatus.SKIPPED)

        status = TestStatus.PASSED if failed == 0 else TestStatus.FAILED

        result = ScenarioResult(
            scenario_id=self.SCENARIO_ID,
            scenario_name=self.SCENARIO_NAME,
            status=status,
            total_tests=len(self.test_results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=duration_ms,
            test_results=self.test_results,
        )

        self._log_scenario_summary(result)
        return result

    def _create_error_result(self, message: str) -> ScenarioResult:
        """Create error ScenarioResult."""
        return ScenarioResult(
            scenario_id=self.SCENARIO_ID,
            scenario_name=self.SCENARIO_NAME,
            status=TestStatus.ERROR,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            duration_ms=0,
            test_results=[],
        )

    # -------------------------------------------------------------------------
    # Logging utilities
    # -------------------------------------------------------------------------

    def log_header(self):
        """Log scenario header."""
        if self.verbose:
            safe_print("\n" + "=" * 70)
            safe_print(f" Scenario: {self.SCENARIO_NAME}")
            safe_print(f" ID: {self.SCENARIO_ID}")
            safe_print("=" * 70)

    def log_info(self, message: str):
        """Log info message."""
        if self.verbose:
            safe_print(f"[INFO] {message}")
        self.logger.info(message)

    def log_success(self, message: str):
        """Log success message."""
        if self.verbose:
            safe_print(f"[PASS] {message}")
        self.logger.info(f"PASS: {message}")

    def log_failure(self, message: str):
        """Log failure message."""
        if self.verbose:
            safe_print(f"[FAIL] {message}")
        self.logger.error(f"FAIL: {message}")

    def _log_test_result(self, result: TestResult):
        """Log individual test result."""
        status_symbol = {
            TestStatus.PASSED: "[PASS]",
            TestStatus.FAILED: "[FAIL]",
            TestStatus.SKIPPED: "[SKIP]",
            TestStatus.ERROR: "[ERROR]",
        }.get(result.status, "[?]")

        if self.verbose:
            safe_print(f"  {status_symbol} {result.test_name} ({result.duration_ms:.0f}ms)")
            if result.message and result.status != TestStatus.PASSED:
                safe_print(f"     -> {result.message}")

    def _log_scenario_summary(self, result: ScenarioResult):
        """Log scenario summary."""
        if self.verbose:
            safe_print("\n" + "-" * 70)
            safe_print(f" Results: {result.passed} passed, {result.failed} failed, {result.skipped} skipped")
            safe_print(f" Total time: {result.duration_ms:.0f}ms")
            safe_print(f" Status: {'PASSED' if result.status == TestStatus.PASSED else 'FAILED'}")
            safe_print("-" * 70 + "\n")

    # -------------------------------------------------------------------------
    # Report generation
    # -------------------------------------------------------------------------

    def save_report(
        self,
        result: ScenarioResult,
        output_dir: str = "claudedocs/uat/sessions",
    ) -> str:
        """
        Save test report to file.

        Args:
            result: ScenarioResult to save
            output_dir: Output directory for reports

        Returns:
            Path to saved report file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.SCENARIO_ID}_{timestamp}.json"
        filepath = output_path / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        self.log_info(f"Report saved to: {filepath}")
        return str(filepath)


# =============================================================================
# Utility functions
# =============================================================================

def run_scenario_sync(scenario_class, **kwargs) -> ScenarioResult:
    """
    Synchronously run a scenario test.

    Args:
        scenario_class: ScenarioTestBase subclass
        **kwargs: Arguments to pass to scenario constructor

    Returns:
        ScenarioResult
    """
    scenario = scenario_class(**kwargs)
    return asyncio.run(scenario.run())


async def run_multiple_scenarios(
    scenario_classes: List[type],
    **kwargs,
) -> List[ScenarioResult]:
    """
    Run multiple scenarios.

    Args:
        scenario_classes: List of ScenarioTestBase subclasses
        **kwargs: Arguments to pass to scenario constructors

    Returns:
        List of ScenarioResult
    """
    results = []
    for scenario_class in scenario_classes:
        scenario = scenario_class(**kwargs)
        result = await scenario.run()
        results.append(result)
    return results
