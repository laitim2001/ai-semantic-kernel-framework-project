"""
Unit tests for Security Penetration Testing (S3-9)

Tests the SecurityTestService and security testing endpoints.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.api.v1.security_testing.routes import (
    SecurityTestService,
    get_security_test_service,
    VulnerabilityCategory,
    Severity,
    TestStatus,
    SecurityTestResult,
    SecurityTestReport,
)


class TestSecurityTestServiceSingleton:
    """Test cases for SecurityTestService singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset(self):
        """Reset singleton before each test."""
        SecurityTestService._instance = None
        yield
        SecurityTestService._instance = None

    def test_singleton_instance(self):
        """Test that SecurityTestService is a singleton."""
        s1 = SecurityTestService()
        s2 = SecurityTestService()
        assert s1 is s2

    def test_get_security_test_service(self):
        """Test get_security_test_service returns singleton."""
        s1 = get_security_test_service()
        s2 = get_security_test_service()
        assert s1 is s2


class TestSQLInjectionTests:
    """Test cases for SQL injection testing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_clean_input_passes(self):
        """Test that clean input passes SQL injection test."""
        result = self.service.test_sql_injection_patterns("Hello World")

        assert result.status == TestStatus.PASSED
        assert result.test_id == "SQL-001"

    def test_sql_select_detected(self):
        """Test that SELECT statement is detected."""
        result = self.service.test_sql_injection_patterns("SELECT * FROM users")

        assert result.status == TestStatus.FAILED
        assert result.severity == Severity.CRITICAL

    def test_sql_drop_detected(self):
        """Test that DROP statement is detected."""
        result = self.service.test_sql_injection_patterns("DROP TABLE users")

        assert result.status == TestStatus.FAILED

    def test_sql_union_detected(self):
        """Test that UNION injection is detected."""
        result = self.service.test_sql_injection_patterns("' UNION SELECT * FROM users--")

        assert result.status == TestStatus.FAILED

    def test_sql_comment_detected(self):
        """Test that SQL comment is detected."""
        result = self.service.test_sql_injection_patterns("admin'--")

        assert result.status == TestStatus.FAILED

    def test_sql_or_1_equals_1_detected(self):
        """Test that OR 1=1 is detected."""
        result = self.service.test_sql_injection_patterns("' OR 1=1 --")

        assert result.status == TestStatus.FAILED

    def test_sql_parameterization_check(self):
        """Test SQL parameterization check."""
        result = self.service.test_sql_parameterization()

        assert result.status == TestStatus.PASSED
        assert "SQLAlchemy ORM" in result.description


class TestXSSTests:
    """Test cases for XSS testing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_clean_input_passes(self):
        """Test that clean input passes XSS test."""
        result = self.service.test_xss_patterns("Hello World")

        assert result.status == TestStatus.PASSED
        assert result.test_id == "XSS-001"

    def test_script_tag_detected(self):
        """Test that script tag is detected."""
        result = self.service.test_xss_patterns("<script>alert('XSS')</script>")

        assert result.status == TestStatus.FAILED
        assert result.severity == Severity.HIGH

    def test_javascript_protocol_detected(self):
        """Test that javascript: protocol is detected."""
        result = self.service.test_xss_patterns("javascript:alert(1)")

        assert result.status == TestStatus.FAILED

    def test_img_onerror_detected(self):
        """Test that img onerror is detected."""
        result = self.service.test_xss_patterns("<img src=x onerror=alert(1)>")

        assert result.status == TestStatus.FAILED

    def test_event_handler_detected(self):
        """Test that onclick handler is detected."""
        result = self.service.test_xss_patterns("<div onclick='alert(1)'>")

        assert result.status == TestStatus.FAILED

    def test_svg_onload_detected(self):
        """Test that SVG onload is detected."""
        result = self.service.test_xss_patterns("<svg onload=alert(1)>")

        assert result.status == TestStatus.FAILED

    def test_html_encoding_clean(self):
        """Test HTML encoding with clean input."""
        result = self.service.test_html_encoding("Hello World")

        assert result.status == TestStatus.PASSED

    def test_html_encoding_special_chars(self):
        """Test HTML encoding with special characters."""
        result = self.service.test_html_encoding("<script>alert('XSS')</script>")

        assert result.status == TestStatus.WARNING
        assert result.severity == Severity.MEDIUM


class TestCSRFTests:
    """Test cases for CSRF testing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_csrf_token_present(self):
        """Test CSRF token presence."""
        headers = {"X-CSRF-Token": "abc123"}
        result = self.service.test_csrf_token_presence(headers)

        assert result.status == TestStatus.PASSED

    def test_csrf_token_missing(self):
        """Test CSRF token missing."""
        headers = {}
        result = self.service.test_csrf_token_presence(headers)

        assert result.status == TestStatus.WARNING
        assert result.severity == Severity.MEDIUM

    def test_xsrf_token_accepted(self):
        """Test X-XSRF-Token is accepted."""
        headers = {"X-XSRF-Token": "abc123"}
        result = self.service.test_csrf_token_presence(headers)

        assert result.status == TestStatus.PASSED

    def test_samesite_cookie(self):
        """Test SameSite cookie check."""
        result = self.service.test_same_site_cookie()

        assert result.status == TestStatus.PASSED


class TestAuthenticationTests:
    """Test cases for authentication testing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_strong_password(self):
        """Test strong password passes."""
        result = self.service.test_password_strength("MyStr0ng!Pass#123")

        assert result.status == TestStatus.PASSED

    def test_weak_password_short(self):
        """Test weak password - too short."""
        result = self.service.test_password_strength("Short1!")

        assert result.status == TestStatus.FAILED
        assert "less than 12" in result.details

    def test_weak_password_no_uppercase(self):
        """Test weak password - no uppercase."""
        result = self.service.test_password_strength("myweakpassword123!")

        assert result.status == TestStatus.FAILED
        assert "uppercase" in result.details

    def test_weak_password_no_special(self):
        """Test weak password - no special chars."""
        result = self.service.test_password_strength("MyWeakPassword123")

        assert result.status == TestStatus.FAILED
        assert "special" in result.details

    def test_jwt_configuration(self):
        """Test JWT configuration check."""
        result = self.service.test_jwt_configuration()

        assert result.status == TestStatus.PASSED

    def test_session_timeout(self):
        """Test session timeout check."""
        result = self.service.test_session_timeout()

        assert result.status == TestStatus.PASSED


class TestSecurityHeaderTests:
    """Test cases for security header testing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_all_headers_present(self):
        """Test all security headers present."""
        headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
        }

        results = self.service.test_security_headers(headers)

        passed_count = sum(1 for r in results if r.status == TestStatus.PASSED)
        assert passed_count == 5

    def test_missing_hsts_header(self):
        """Test missing HSTS header."""
        headers = {}

        results = self.service.test_security_headers(headers)

        hsts_result = next(r for r in results if r.test_id == "HDR-001")
        assert hsts_result.status == TestStatus.FAILED
        assert hsts_result.severity == Severity.HIGH

    def test_missing_csp_header(self):
        """Test missing CSP header."""
        headers = {}

        results = self.service.test_security_headers(headers)

        csp_result = next(r for r in results if r.test_id == "HDR-002")
        assert csp_result.status == TestStatus.FAILED
        assert csp_result.severity == Severity.MEDIUM


class TestCryptographyTests:
    """Test cases for cryptography testing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_encryption_algorithm(self):
        """Test encryption algorithm check."""
        result = self.service.test_encryption_algorithm()

        assert result.status == TestStatus.PASSED
        assert "AES-256-GCM" in result.description

    def test_key_management(self):
        """Test key management check."""
        result = self.service.test_key_management()

        assert result.status == TestStatus.PASSED


class TestAccessControlTests:
    """Test cases for access control testing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_rbac_implementation(self):
        """Test RBAC implementation check."""
        result = self.service.test_rbac_implementation()

        assert result.status == TestStatus.PASSED
        assert "4 roles" in result.details

    def test_permission_checks(self):
        """Test permission check decorators."""
        result = self.service.test_permission_checks()

        assert result.status == TestStatus.PASSED


class TestSecurityReportGeneration:
    """Test cases for security report generation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_full_scan_generates_report(self):
        """Test that full scan generates a report."""
        report = self.service.run_full_security_scan()

        assert report.report_id is not None
        assert report.started_at is not None
        assert report.completed_at is not None
        assert report.total_tests > 0
        assert len(report.results) > 0

    def test_report_has_correct_counts(self):
        """Test that report has correct counts."""
        report = self.service.run_full_security_scan()

        assert report.passed + report.failed + report.warnings <= report.total_tests

    def test_report_can_be_retrieved(self):
        """Test that report can be retrieved by ID."""
        report = self.service.run_full_security_scan()
        retrieved = self.service.get_report(report.report_id)

        assert retrieved is not None
        assert retrieved.report_id == report.report_id

    def test_nonexistent_report_returns_none(self):
        """Test that nonexistent report returns None."""
        retrieved = self.service.get_report("nonexistent-id")

        assert retrieved is None

    def test_full_scan_with_malicious_input(self):
        """Test full scan with malicious input."""
        report = self.service.run_full_security_scan(
            test_input="'; DROP TABLE users; --"
        )

        # Should detect SQL injection
        sql_results = [r for r in report.results if "SQL" in r.test_id]
        assert any(r.status == TestStatus.FAILED for r in sql_results)


class TestDataClasses:
    """Test cases for data classes."""

    def test_security_test_result_creation(self):
        """Test SecurityTestResult creation."""
        result = SecurityTestResult(
            test_id="TEST-001",
            test_name="Test Result",
            category=VulnerabilityCategory.INJECTION,
            status=TestStatus.PASSED,
            severity=Severity.INFO,
            description="Test description",
        )

        assert result.test_id == "TEST-001"
        assert result.category == VulnerabilityCategory.INJECTION
        assert result.status == TestStatus.PASSED
        assert isinstance(result.timestamp, datetime)

    def test_security_test_report_creation(self):
        """Test SecurityTestReport creation."""
        report = SecurityTestReport(
            report_id="report-123",
            started_at=datetime.utcnow(),
            completed_at=None,
            total_tests=10,
            passed=8,
            failed=2,
            warnings=0,
        )

        assert report.report_id == "report-123"
        assert report.total_tests == 10
        assert len(report.results) == 0


class TestEnums:
    """Test cases for enums."""

    def test_vulnerability_categories(self):
        """Test VulnerabilityCategory enum values."""
        assert VulnerabilityCategory.INJECTION == "A03:2021-Injection"
        assert VulnerabilityCategory.BROKEN_AUTH == "A07:2021-Identification and Authentication Failures"
        assert VulnerabilityCategory.BROKEN_ACCESS == "A01:2021-Broken Access Control"

    def test_severity_levels(self):
        """Test Severity enum values."""
        assert Severity.CRITICAL == "P0-Critical"
        assert Severity.HIGH == "P1-High"
        assert Severity.MEDIUM == "P2-Medium"
        assert Severity.LOW == "P3-Low"
        assert Severity.INFO == "P4-Info"

    def test_test_status(self):
        """Test TestStatus enum values."""
        assert TestStatus.PASSED == "passed"
        assert TestStatus.FAILED == "failed"
        assert TestStatus.WARNING == "warning"
        assert TestStatus.SKIPPED == "skipped"


class TestResponseModels:
    """Test cases for response models."""

    def test_routes_import(self):
        """Test that routes can be imported."""
        from src.api.v1.security_testing.routes import router
        assert router is not None

    def test_response_models(self):
        """Test Pydantic response models."""
        from src.api.v1.security_testing.routes import (
            TestResultResponse,
            SecurityReportResponse,
            VulnerabilitySummaryResponse,
            SecurityHealthResponse,
        )

        # Test TestResultResponse
        result = TestResultResponse(
            test_id="TEST-001",
            test_name="Test",
            category="A03:2021-Injection",
            status="passed",
            severity="P4-Info",
            description="Test description",
            details="",
            remediation="",
            timestamp="2025-01-01T00:00:00",
        )
        assert result.test_id == "TEST-001"

        # Test VulnerabilitySummaryResponse
        summary = VulnerabilitySummaryResponse(
            critical=0,
            high=1,
            medium=2,
            low=3,
            info=4,
            total=10,
        )
        assert summary.total == 10

        # Test SecurityHealthResponse
        health = SecurityHealthResponse(
            status="healthy",
            pass_rate=95.0,
            critical_issues=0,
            high_issues=0,
            healthy=True,
            last_scan="2025-01-01T00:00:00",
        )
        assert health.healthy is True


class TestOWASPCoverage:
    """Test cases for OWASP Top 10 coverage."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up for each test."""
        SecurityTestService._instance = None
        self.service = get_security_test_service()
        yield
        SecurityTestService._instance = None

    def test_all_owasp_categories_tested(self):
        """Test that all OWASP categories are covered."""
        report = self.service.run_full_security_scan()

        categories = set(r.category for r in report.results)

        # Check that we have coverage for key OWASP categories
        assert VulnerabilityCategory.INJECTION in categories
        assert VulnerabilityCategory.BROKEN_AUTH in categories
        assert VulnerabilityCategory.SECURITY_MISCONFIG in categories
        assert VulnerabilityCategory.CRYPTO_FAILURES in categories
        assert VulnerabilityCategory.BROKEN_ACCESS in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
