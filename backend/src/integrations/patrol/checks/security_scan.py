"""
Security Scan Check - 安全掃描檢查

Sprint 82 - S82-1: 主動巡檢模式
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from ..types import CheckResult, CheckType, PatrolStatus
from .base import BaseCheck

logger = logging.getLogger(__name__)


class SecurityScanCheck(BaseCheck):
    """
    安全掃描檢查

    檢查常見安全問題，如敏感信息洩露、配置問題等
    """

    check_type = CheckType.SECURITY_SCAN
    check_name = "Security Scan Check"
    description = "Scan for common security vulnerabilities and misconfigurations"

    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        (r"password\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded password"),
        (r"api[_-]?key\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
        (r"secret\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
        (r"token\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded token"),
        (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "Private key exposure"),
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "Email address (potential PII)"),
        (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "Potential credit card number"),
    ]

    # 危險配置模式
    DANGEROUS_CONFIG_PATTERNS = [
        (r"DEBUG\s*[=:]\s*[Tt]rue", "Debug mode enabled"),
        (r"ALLOW_ALL_ORIGINS", "CORS all origins allowed"),
        (r"verify\s*[=:]\s*[Ff]alse", "SSL verification disabled"),
        (r"insecure\s*[=:]\s*[Tt]rue", "Insecure mode enabled"),
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 掃描類型
        self.scan_types: List[str] = self.get_config_value(
            "scan_types",
            ["sensitive_data", "dangerous_config", "file_permissions"],
        )

        # 嚴重性閾值
        self.severity_threshold: str = self.get_config_value("severity_threshold", "medium")
        self.skip_low_severity: bool = self.get_config_value("skip_low_severity", True)

        # 掃描路徑
        self.scan_paths: List[str] = self.get_config_value(
            "scan_paths",
            ["backend/", "frontend/", ".env"],
        )

        # 排除路徑
        self.exclude_patterns: List[str] = self.get_config_value(
            "exclude_patterns",
            [r"node_modules", r"__pycache__", r"\.git", r"\.venv", r"venv"],
        )

        # 文件類型
        self.scan_extensions: List[str] = self.get_config_value(
            "scan_extensions",
            [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env", ".config"],
        )

    async def execute(self) -> CheckResult:
        """執行安全掃描檢查"""
        self._start_check()

        findings: List[Dict[str, Any]] = []
        files_scanned: int = 0
        metrics: Dict[str, float] = {
            "files_scanned": 0,
            "high_severity_count": 0,
            "medium_severity_count": 0,
            "low_severity_count": 0,
            "total_findings": 0,
        }

        # 執行各類掃描
        if "sensitive_data" in self.scan_types:
            sensitive_findings = await self._scan_sensitive_data()
            findings.extend(sensitive_findings)

        if "dangerous_config" in self.scan_types:
            config_findings = await self._scan_dangerous_config()
            findings.extend(config_findings)

        if "file_permissions" in self.scan_types:
            permission_findings = await self._check_file_permissions()
            findings.extend(permission_findings)

        # 環境檢查
        env_findings = await self._check_environment()
        findings.extend(env_findings)

        # 統計嚴重性
        for finding in findings:
            severity = finding.get("severity", "low")
            if severity == "high":
                metrics["high_severity_count"] += 1
            elif severity == "medium":
                metrics["medium_severity_count"] += 1
            else:
                metrics["low_severity_count"] += 1

        metrics["total_findings"] = float(len(findings))
        metrics["files_scanned"] = float(files_scanned)

        # 過濾低嚴重性
        if self.skip_low_severity:
            findings = [f for f in findings if f.get("severity") != "low"]

        # 彙總結果
        details = {
            "findings": findings[:20],  # 限制數量
            "total_findings": len(findings),
            "scan_types": self.scan_types,
            "severity_breakdown": {
                "high": int(metrics["high_severity_count"]),
                "medium": int(metrics["medium_severity_count"]),
                "low": int(metrics["low_severity_count"]),
            },
        }

        # 確定狀態
        if metrics["high_severity_count"] > 0:
            return self._critical(
                message=f"Found {int(metrics['high_severity_count'])} high-severity security issues",
                details=details,
                metrics=metrics,
                errors=[f["description"] for f in findings if f.get("severity") == "high"][:5],
            )
        elif metrics["medium_severity_count"] > 0:
            return self._warning(
                message=f"Found {int(metrics['medium_severity_count'])} medium-severity security issues",
                details=details,
                metrics=metrics,
            )
        else:
            return self._healthy(
                message="No significant security issues found",
                details=details,
                metrics=metrics,
            )

    async def _scan_sensitive_data(self) -> List[Dict[str, Any]]:
        """掃描敏感數據"""
        findings: List[Dict[str, Any]] = []

        for scan_path in self.scan_paths:
            if not os.path.exists(scan_path):
                continue

            files = self._get_files_to_scan(scan_path)

            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    for pattern, description in self.SENSITIVE_PATTERNS:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            findings.append({
                                "type": "sensitive_data",
                                "severity": "high" if "password" in description.lower() or "key" in description.lower() else "medium",
                                "file": file_path,
                                "description": description,
                                "match_count": len(matches),
                                "recommendation": f"Remove or secure {description.lower()}",
                            })

                except Exception as e:
                    logger.debug(f"Failed to scan {file_path}: {e}")

        return findings

    async def _scan_dangerous_config(self) -> List[Dict[str, Any]]:
        """掃描危險配置"""
        findings: List[Dict[str, Any]] = []

        for scan_path in self.scan_paths:
            if not os.path.exists(scan_path):
                continue

            files = self._get_files_to_scan(scan_path)

            for file_path in files:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    for pattern, description in self.DANGEROUS_CONFIG_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            findings.append({
                                "type": "dangerous_config",
                                "severity": "medium",
                                "file": file_path,
                                "description": description,
                                "recommendation": f"Review and disable {description.lower()} in production",
                            })

                except Exception as e:
                    logger.debug(f"Failed to scan {file_path}: {e}")

        return findings

    async def _check_file_permissions(self) -> List[Dict[str, Any]]:
        """檢查文件權限"""
        findings: List[Dict[str, Any]] = []

        # 檢查敏感文件的權限
        sensitive_files = [".env", ".env.local", "credentials.json", "secrets.yaml"]

        for scan_path in self.scan_paths:
            if not os.path.exists(scan_path):
                continue

            for sensitive_file in sensitive_files:
                file_path = os.path.join(scan_path, sensitive_file) if os.path.isdir(scan_path) else scan_path

                if os.path.exists(file_path):
                    try:
                        # Unix 系統檢查權限
                        if os.name != "nt":
                            mode = oct(os.stat(file_path).st_mode)[-3:]
                            if mode != "600" and mode != "400":
                                findings.append({
                                    "type": "file_permissions",
                                    "severity": "medium",
                                    "file": file_path,
                                    "description": f"Sensitive file has loose permissions ({mode})",
                                    "recommendation": "Set file permissions to 600 or 400",
                                })
                    except Exception as e:
                        logger.debug(f"Failed to check permissions for {file_path}: {e}")

        return findings

    async def _check_environment(self) -> List[Dict[str, Any]]:
        """檢查環境配置"""
        findings: List[Dict[str, Any]] = []

        # 檢查危險環境變量
        dangerous_env_vars = {
            "DEBUG": ("true", "1"),
            "FLASK_DEBUG": ("true", "1"),
            "DJANGO_DEBUG": ("true", "1"),
        }

        for var_name, dangerous_values in dangerous_env_vars.items():
            value = os.environ.get(var_name, "").lower()
            if value in dangerous_values:
                findings.append({
                    "type": "environment",
                    "severity": "medium",
                    "description": f"Environment variable {var_name} is set to {value}",
                    "recommendation": f"Disable {var_name} in production environment",
                })

        # 檢查是否缺少必要的安全配置
        security_env_vars = ["SECRET_KEY", "JWT_SECRET"]
        for var_name in security_env_vars:
            if not os.environ.get(var_name):
                findings.append({
                    "type": "environment",
                    "severity": "low",
                    "description": f"Security variable {var_name} not set",
                    "recommendation": f"Set {var_name} environment variable",
                })

        return findings

    def _get_files_to_scan(self, path: str) -> List[str]:
        """獲取要掃描的文件列表"""
        files: List[str] = []

        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for root, _, filenames in os.walk(path):
                # 檢查是否應該排除
                should_exclude = False
                for pattern in self.exclude_patterns:
                    if re.search(pattern, root):
                        should_exclude = True
                        break

                if should_exclude:
                    continue

                for filename in filenames:
                    # 檢查文件擴展名
                    _, ext = os.path.splitext(filename)
                    if ext in self.scan_extensions:
                        files.append(os.path.join(root, filename))

        return files[:100]  # 限制文件數量
