"""
Log Analysis Check - 日誌分析檢查

Sprint 82 - S82-1: 主動巡檢模式
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..types import CheckResult, CheckType, PatrolStatus
from .base import BaseCheck

logger = logging.getLogger(__name__)


class LogAnalysisCheck(BaseCheck):
    """
    日誌分析檢查

    分析日誌文件中的錯誤和警告模式
    """

    check_type = CheckType.LOG_ANALYSIS
    check_name = "Log Analysis Check"
    description = "Analyze log files for errors and warnings"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 錯誤模式
        self.error_patterns: List[str] = self.get_config_value(
            "error_patterns",
            [r"ERROR", r"CRITICAL", r"FATAL", r"Exception", r"Traceback"],
        )

        # 警告模式
        self.warning_patterns: List[str] = self.get_config_value(
            "warning_patterns",
            [r"WARN", r"WARNING"],
        )

        # 時間窗口（分鐘）
        self.time_window_minutes: int = self.get_config_value("time_window_minutes", 60)

        # 閾值
        self.max_error_count: int = self.get_config_value("max_error_count", 10)
        self.max_warning_count: int = self.get_config_value("max_warning_count", 50)

        # 日誌路徑
        self.log_paths: List[str] = self.get_config_value(
            "log_paths",
            [
                "logs/",
                "/var/log/",
            ],
        )

        # 日誌文件模式
        self.log_file_patterns: List[str] = self.get_config_value(
            "log_file_patterns",
            [r".*\.log$", r".*\.log\.\d+$"],
        )

    async def execute(self) -> CheckResult:
        """執行日誌分析檢查"""
        self._start_check()

        all_errors: List[Dict[str, Any]] = []
        all_warnings: List[Dict[str, Any]] = []
        analyzed_files: List[str] = []
        metrics: Dict[str, float] = {
            "total_errors": 0,
            "total_warnings": 0,
            "files_analyzed": 0,
            "total_lines_scanned": 0,
        }

        # 計算時間窗口
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.time_window_minutes)

        # 分析每個日誌路徑
        for log_path in self.log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                log_files = self._find_log_files(log_path)

                for log_file in log_files:
                    file_result = await self._analyze_log_file(log_file, cutoff_time)
                    all_errors.extend(file_result["errors"])
                    all_warnings.extend(file_result["warnings"])
                    metrics["total_lines_scanned"] += file_result["lines_scanned"]
                    analyzed_files.append(log_file)

            except Exception as e:
                logger.error(f"Failed to analyze logs in {log_path}: {e}")

        metrics["total_errors"] = float(len(all_errors))
        metrics["total_warnings"] = float(len(all_warnings))
        metrics["files_analyzed"] = float(len(analyzed_files))

        # 錯誤率（每千行）
        if metrics["total_lines_scanned"] > 0:
            metrics["error_rate_per_1k"] = (
                metrics["total_errors"] / metrics["total_lines_scanned"] * 1000
            )
            metrics["warning_rate_per_1k"] = (
                metrics["total_warnings"] / metrics["total_lines_scanned"] * 1000
            )
        else:
            metrics["error_rate_per_1k"] = 0
            metrics["warning_rate_per_1k"] = 0

        # 彙總結果
        details = {
            "time_window_minutes": self.time_window_minutes,
            "files_analyzed": analyzed_files[:10],  # 只顯示前 10 個
            "total_files": len(analyzed_files),
            "error_summary": self._summarize_issues(all_errors)[:10],
            "warning_summary": self._summarize_issues(all_warnings)[:10],
            "recent_errors": all_errors[:5],  # 最近 5 個錯誤
        }

        # 確定狀態
        error_count = len(all_errors)
        warning_count = len(all_warnings)

        if error_count > self.max_error_count:
            return self._critical(
                message=f"Found {error_count} errors in logs (threshold: {self.max_error_count})",
                details=details,
                metrics=metrics,
                errors=[e["message"][:100] for e in all_errors[:5]],
            )
        elif warning_count > self.max_warning_count or error_count > 0:
            return self._warning(
                message=f"Found {error_count} errors and {warning_count} warnings in logs",
                details=details,
                metrics=metrics,
            )
        else:
            return self._healthy(
                message=f"No significant issues in {len(analyzed_files)} log files",
                details=details,
                metrics=metrics,
            )

    def _find_log_files(self, path: str) -> List[str]:
        """查找日誌文件"""
        log_files: List[str] = []

        if os.path.isfile(path):
            log_files.append(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    for pattern in self.log_file_patterns:
                        if re.match(pattern, file):
                            log_files.append(os.path.join(root, file))
                            break

        return log_files[:20]  # 限制文件數量

    async def _analyze_log_file(
        self,
        file_path: str,
        cutoff_time: datetime,
    ) -> Dict[str, Any]:
        """分析單個日誌文件"""
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        lines_scanned = 0

        try:
            # 只讀取最後 10000 行
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-10000:]

            for line_num, line in enumerate(lines, 1):
                lines_scanned += 1

                # 檢查錯誤模式
                for pattern in self.error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        errors.append({
                            "file": file_path,
                            "line": line_num,
                            "message": line.strip()[:200],
                            "pattern": pattern,
                        })
                        break

                # 檢查警告模式
                for pattern in self.warning_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        warnings.append({
                            "file": file_path,
                            "line": line_num,
                            "message": line.strip()[:200],
                            "pattern": pattern,
                        })
                        break

        except Exception as e:
            logger.error(f"Failed to read log file {file_path}: {e}")

        return {
            "errors": errors,
            "warnings": warnings,
            "lines_scanned": lines_scanned,
        }

    def _summarize_issues(
        self,
        issues: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """彙總問題（按模式分組）"""
        pattern_counts: Dict[str, int] = {}
        pattern_examples: Dict[str, str] = {}

        for issue in issues:
            pattern = issue.get("pattern", "unknown")
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            if pattern not in pattern_examples:
                pattern_examples[pattern] = issue.get("message", "")[:100]

        summary = [
            {
                "pattern": pattern,
                "count": count,
                "example": pattern_examples.get(pattern, ""),
            }
            for pattern, count in sorted(
                pattern_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ]

        return summary
