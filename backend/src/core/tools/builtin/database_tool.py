"""
Database Tool for executing database queries

Supports SELECT queries with parameter binding for safe execution.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import ITool, ToolExecutionResult

logger = logging.getLogger(__name__)


class DatabaseTool(ITool):
    """
    Database Tool 實作

    用於執行資料庫查詢 (僅支援 SELECT 查詢以確保安全性)
    """

    def __init__(self, session: AsyncSession, read_only: bool = True):
        """
        初始化 Database Tool

        Args:
            session: SQLAlchemy AsyncSession
            read_only: 是否僅允許 SELECT 查詢 (預設: True)
        """
        self.session = session
        self.read_only = read_only

    @property
    def name(self) -> str:
        return "database"

    @property
    def description(self) -> str:
        mode = "Read-only" if self.read_only else "Read-write"
        return f"{mode} database query execution with parameter binding"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute (SELECT only in read-only mode)",
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters for safe parameter binding (optional)",
                    "additionalProperties": True,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return (optional, default: 1000)",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 10000,
                },
            },
        }

    def _is_safe_query(self, query: str) -> bool:
        """
        檢查查詢是否安全 (僅 SELECT)

        Args:
            query: SQL 查詢

        Returns:
            True 如果查詢安全
        """
        # Normalize query
        normalized_query = query.strip().upper()

        # Allow SELECT, WITH (for CTEs), and EXPLAIN
        safe_prefixes = ["SELECT", "WITH", "EXPLAIN"]

        for prefix in safe_prefixes:
            if normalized_query.startswith(prefix):
                return True

        return False

    async def execute(self, **kwargs) -> ToolExecutionResult:
        """
        執行資料庫查詢

        Args:
            query: SQL 查詢
            params: 查詢參數 (optional)
            limit: 最大返回行數 (optional)

        Returns:
            ToolExecutionResult 包含查詢結果
        """
        start_time = datetime.now(timezone.utc)

        query = kwargs.get("query")
        params = kwargs.get("params", {})
        limit = kwargs.get("limit", 1000)

        # Validate query safety in read-only mode
        if self.read_only and not self._is_safe_query(query):
            logger.warning(f"Unsafe query blocked: {query}")
            return ToolExecutionResult(
                success=False,
                output=None,
                error_message="Only SELECT queries are allowed in read-only mode",
                execution_time_ms=0,
                metadata={"query": query, "read_only": self.read_only},
            )

        try:
            # Execute query
            result = await self.session.execute(text(query), params)

            # Fetch results
            rows = result.fetchmany(limit)

            # Convert to dict format
            columns = list(result.keys()) if result.keys() else []
            rows_data = [dict(zip(columns, row)) for row in rows]

            # Calculate execution time
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            output = {
                "rows": rows_data,
                "count": len(rows_data),
                "columns": columns,
                "limited": len(rows_data) >= limit,
            }

            logger.info(
                f"Database query executed successfully, returned {len(rows_data)} rows"
            )

            return ToolExecutionResult(
                success=True,
                output=output,
                execution_time_ms=execution_time_ms,
                metadata={
                    "query": query,
                    "row_count": len(rows_data),
                    "column_count": len(columns),
                },
            )

        except Exception as e:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"Database query failed: {e}")

            # Rollback transaction on error
            await self.session.rollback()

            return ToolExecutionResult(
                success=False,
                output=None,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
                metadata={"query": query, "error_type": type(e).__name__},
            )

    def validate_parameters(self, params: Dict[str, Any]) -> None:
        """
        驗證參數

        Args:
            params: 要驗證的參數

        Raises:
            ValueError: 參數驗證失敗
        """
        super().validate_parameters(params)

        query = params.get("query", "")

        # Basic validation
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Check for common SQL injection patterns
        dangerous_keywords = [
            "DROP ",
            "DELETE ",
            "TRUNCATE ",
            "ALTER ",
            "CREATE ",
            "GRANT ",
            "REVOKE ",
            "; DROP",
            "; DELETE",
        ]

        upper_query = query.upper()
        for keyword in dangerous_keywords:
            if keyword in upper_query:
                raise ValueError(f"Potentially dangerous SQL keyword detected: {keyword.strip()}")

        # Validate limit parameter
        limit = params.get("limit", 1000)
        if not isinstance(limit, int) or limit < 1 or limit > 10000:
            raise ValueError("Limit must be an integer between 1 and 10000")
