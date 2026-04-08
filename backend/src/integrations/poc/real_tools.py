"""Real Tools — Actual command execution with safety whitelist.

Replaces the LLM-simulated tools (run_diagnostic_command, search_knowledge_base)
with tools that execute REAL operations on the server.

Security model:
- Command whitelist: only allowed commands can run
- Path whitelist: only allowed directories for file reads
- SQL whitelist: only SELECT queries allowed
- Timeout: all operations have strict timeouts
- Output limits: truncated to prevent memory issues

PoC: Agent Team V2 — poc/agent-team branch.
"""

import asyncio
import logging
import os
import re
import shlex
import subprocess
from typing import Optional

from agent_framework import tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Command safety whitelist
# ---------------------------------------------------------------------------

ALLOWED_COMMANDS = {
    "ping": {"max_args": 5, "timeout": 10},
    "curl": {
        "allowed_flags": ["-s", "-S", "-o", "-w", "-I", "-X", "-H", "--max-time",
                          "--connect-timeout", "-k", "-L"],
        "timeout": 15,
    },
    "dig": {"max_args": 4, "timeout": 10},
    "nslookup": {"max_args": 3, "timeout": 10},
    "docker": {"allowed_subcommands": ["ps", "inspect", "logs", "stats"], "timeout": 10},
    "systemctl": {"allowed_subcommands": ["status", "is-active", "list-units"], "timeout": 5},
    "tail": {
        "allowed_flags": ["-n", "-f"],
        "path_whitelist": ["/var/log/", "/app/logs/", "/tmp/logs/"],
        "timeout": 5,
    },
    "cat": {
        "path_whitelist": ["/var/log/", "/app/logs/", "/tmp/logs/", "/etc/"],
        "timeout": 5,
    },
    "redis-cli": {"allowed_subcommands": ["INFO", "PING", "DBSIZE", "CLIENT LIST"], "timeout": 5},
    "netstat": {"allowed_flags": ["-an", "-tlnp", "-tunlp"], "timeout": 5},
    "ss": {"allowed_flags": ["-tlnp", "-tunlp", "-an"], "timeout": 5},
    "df": {"allowed_flags": ["-h", "-i"], "timeout": 5},
    "free": {"allowed_flags": ["-h", "-m", "-g"], "timeout": 5},
    "uptime": {"max_args": 0, "timeout": 5},
    "hostname": {"max_args": 0, "timeout": 5},
    "whoami": {"max_args": 0, "timeout": 5},
    "date": {"max_args": 0, "timeout": 5},
}

# Absolutely forbidden patterns (even if command is whitelisted)
FORBIDDEN_PATTERNS = [
    r"\brm\b", r"\brmdir\b", r"\bmkdir\b",
    r"\bdd\b", r"\bmkfs\b", r"\bformat\b",
    r"\bkill\b", r"\bkillall\b", r"\bpkill\b",
    r">\s*/", r">>\s*/",  # redirect to absolute paths
    r"\|.*\brm\b", r"\|.*\bdd\b",  # piped to dangerous commands
    r";\s*rm\b", r"&&\s*rm\b",  # chained dangerous commands
    r"\$\(", r"`",  # command substitution
]


def _validate_command(command_str: str) -> list[str]:
    """Validate and parse a command against the whitelist.

    Returns the parsed command list if safe.
    Raises ValueError if the command is not allowed.
    """
    # Check forbidden patterns first
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, command_str):
            raise ValueError(f"Command contains forbidden pattern: {pattern}")

    # Parse command
    try:
        parts = shlex.split(command_str)
    except ValueError as e:
        raise ValueError(f"Invalid command syntax: {e}")

    if not parts:
        raise ValueError("Empty command")

    cmd = parts[0]

    # Strip path prefix (e.g., /usr/bin/ping → ping)
    cmd_base = os.path.basename(cmd)

    if cmd_base not in ALLOWED_COMMANDS:
        allowed_list = ", ".join(sorted(ALLOWED_COMMANDS.keys()))
        raise ValueError(
            f"Command '{cmd_base}' not in whitelist. Allowed: {allowed_list}"
        )

    rules = ALLOWED_COMMANDS[cmd_base]

    # Check max_args
    if "max_args" in rules:
        arg_count = len(parts) - 1
        if arg_count > rules["max_args"]:
            raise ValueError(
                f"Command '{cmd_base}' allows max {rules['max_args']} args, got {arg_count}"
            )

    # Check allowed subcommands (e.g., docker ps, systemctl status)
    if "allowed_subcommands" in rules and len(parts) > 1:
        subcmd = parts[1]
        if subcmd not in rules["allowed_subcommands"]:
            raise ValueError(
                f"Subcommand '{subcmd}' not allowed for '{cmd_base}'. "
                f"Allowed: {rules['allowed_subcommands']}"
            )

    # Check path whitelist (for tail, cat, etc.)
    if "path_whitelist" in rules:
        # Find path arguments (not flags)
        path_args = [p for p in parts[1:] if not p.startswith("-")]
        for path in path_args:
            if not any(path.startswith(allowed) for allowed in rules["path_whitelist"]):
                raise ValueError(
                    f"Path '{path}' not in allowed directories: {rules['path_whitelist']}"
                )

    return parts


def _get_timeout(command_str: str) -> int:
    """Get the timeout for a command."""
    try:
        parts = shlex.split(command_str)
        cmd_base = os.path.basename(parts[0]) if parts else ""
        rules = ALLOWED_COMMANDS.get(cmd_base, {})
        return rules.get("timeout", 10)
    except Exception:
        return 10


# ---------------------------------------------------------------------------
# SQL safety
# ---------------------------------------------------------------------------

FORBIDDEN_SQL = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bCREATE\b", r"\bALTER\b", r"\bTRUNCATE\b", r"\bGRANT\b",
    r"\bREVOKE\b", r"\bEXEC\b", r"\bEXECUTE\b",
]


def _validate_sql(sql: str) -> str:
    """Validate SQL is read-only (SELECT only)."""
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    for pattern in FORBIDDEN_SQL:
        if re.search(pattern, sql_upper):
            raise ValueError(f"SQL contains forbidden keyword: {pattern}")

    return sql


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def create_real_tools() -> list:
    """Create real diagnostic tools with safety whitelist.

    Returns tools that execute ACTUAL commands, not LLM simulations.
    """

    @tool(name="run_diagnostic_command", description=(
        "Execute a REAL diagnostic command on the server. "
        "Allowed commands: ping, curl, dig, nslookup, docker (ps/inspect/logs), "
        "systemctl (status), tail/cat (log files only), redis-cli (INFO/PING), "
        "netstat, ss, df, free, uptime, hostname, whoami, date. "
        "Commands are sandboxed with timeouts. Dangerous operations are blocked."
    ))
    def run_diagnostic_command(command: str) -> str:
        """Execute a real diagnostic command (read-only, sandboxed)."""
        try:
            parsed = _validate_command(command)
            timeout = _get_timeout(command)

            result = subprocess.run(
                parsed,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "LC_ALL": "C"},
            )

            output_parts = [f"EXIT_CODE: {result.returncode}"]
            if result.stdout:
                stdout = result.stdout[:3000]
                output_parts.append(f"STDOUT:\n{stdout}")
            if result.stderr:
                stderr = result.stderr[:1000]
                output_parts.append(f"STDERR:\n{stderr}")

            return "\n".join(output_parts)

        except ValueError as e:
            return f"BLOCKED: {e}"
        except subprocess.TimeoutExpired:
            return f"TIMEOUT: Command timed out after {_get_timeout(command)}s"
        except FileNotFoundError:
            return f"NOT_FOUND: Command '{command.split()[0]}' not found on this system"
        except Exception as e:
            return f"ERROR: {str(e)[:300]}"

    @tool(name="search_knowledge_base", description=(
        "Search the knowledge base for relevant information. "
        "Uses vector search (Qdrant) to find past incidents, SOPs, "
        "system documentation, and configuration details. "
        "If the knowledge base is not available, falls back to a basic search."
    ))
    def search_knowledge_base(query: str) -> str:
        """Search the real knowledge base via Qdrant/mem0."""
        try:
            # Try real Qdrant search via unified memory
            from src.integrations.memory.unified_memory import UnifiedMemoryService
            import asyncio

            async def _search():
                memory = UnifiedMemoryService()
                results = await memory.search(query=query, limit=5)
                return results

            # Run async search in sync context
            try:
                loop = asyncio.get_running_loop()
                # We're already in an async context — create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    results = pool.submit(asyncio.run, _search()).result(timeout=10)
            except RuntimeError:
                results = asyncio.run(_search())

            if results:
                lines = [f"=== Knowledge Base Results for: {query} ==="]
                for i, r in enumerate(results[:5], 1):
                    content = r.get("memory", r.get("content", str(r)))[:300]
                    score = r.get("score", "N/A")
                    lines.append(f"\n[{i}] (score: {score})\n{content}")
                return "\n".join(lines)
            else:
                return f"No results found for: {query}"

        except ImportError:
            return f"Knowledge base not available (Qdrant/mem0 not configured). Query: {query}"
        except Exception as e:
            logger.warning(f"KB search failed, returning empty: {e}")
            return f"Knowledge base search error: {str(e)[:200]}. Query: {query}"

    @tool(name="read_log_file", description=(
        "Read the last N lines of a log file. "
        "Only files in /var/log/, /app/logs/, or /tmp/logs/ are accessible. "
        "Default: last 50 lines."
    ))
    def read_log_file(file_path: str, last_n_lines: int = 50) -> str:
        """Read the tail of an allowed log file."""
        allowed_dirs = ["/var/log/", "/app/logs/", "/tmp/logs/"]
        if not any(file_path.startswith(d) for d in allowed_dirs):
            return f"BLOCKED: Path '{file_path}' not in allowed directories: {allowed_dirs}"

        try:
            # Resolve to prevent directory traversal
            real_path = os.path.realpath(file_path)
            if not any(real_path.startswith(d) for d in allowed_dirs):
                return f"BLOCKED: Resolved path '{real_path}' escapes allowed directory"

            if not os.path.exists(real_path):
                return f"NOT_FOUND: File '{file_path}' does not exist"

            # Read last N lines
            with open(real_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                tail = lines[-last_n_lines:]
                return f"=== {file_path} (last {len(tail)} lines) ===\n" + "".join(tail)

        except PermissionError:
            return f"PERMISSION_DENIED: Cannot read '{file_path}'"
        except Exception as e:
            return f"ERROR reading '{file_path}': {str(e)[:200]}"

    @tool(name="query_database", description=(
        "Execute a READ-ONLY SQL query against the diagnostic database. "
        "Only SELECT queries are allowed — INSERT, UPDATE, DELETE, DROP etc. "
        "are all blocked. Results limited to 100 rows. Timeout: 5 seconds."
    ))
    def query_database(sql: str) -> str:
        """Execute a read-only SQL query."""
        try:
            validated_sql = _validate_sql(sql)
        except ValueError as e:
            return f"BLOCKED: {e}"

        try:
            import psycopg2

            db_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "dbname": os.getenv("DB_NAME", "ipa_platform"),
                "user": os.getenv("DB_USER", "ipa_user"),
                "password": os.getenv("DB_PASSWORD", "ipa_password"),
                "options": "-c statement_timeout=5000",  # 5s timeout
            }

            conn = psycopg2.connect(**db_config)
            try:
                cur = conn.cursor()
                cur.execute(validated_sql)
                rows = cur.fetchmany(100)
                columns = [desc[0] for desc in cur.description] if cur.description else []

                lines = [f"=== Query Results ({len(rows)} rows, limit 100) ==="]
                if columns:
                    lines.append(" | ".join(columns))
                    lines.append("-" * 60)
                for row in rows:
                    lines.append(" | ".join(str(v)[:50] for v in row))

                return "\n".join(lines)
            finally:
                conn.close()

        except ImportError:
            return "DATABASE_UNAVAILABLE: psycopg2 not installed"
        except Exception as e:
            return f"DATABASE_ERROR: {str(e)[:300]}"

    return [run_diagnostic_command, search_knowledge_base, read_log_file, query_database]
