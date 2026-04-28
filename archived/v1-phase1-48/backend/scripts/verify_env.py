#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
環境驗證腳本: 檢查 IPA Platform 開發環境設置

此腳本會檢查：
1. Python 版本和關鍵依賴版本
2. 資料庫連接和 Schema 正確性
3. 必要的環境變數

使用方式:
    py -3.13 backend/scripts/verify_env.py

返回碼:
    0: 所有檢查通過
    1: 有檢查失敗
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# 修復 Windows 控制台編碼問題
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 將 backend 目錄添加到 Python path
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))


def print_section(title: str) -> None:
    """Print section header."""
    print(f"\n[{title}]")


def check_python_version() -> Tuple[bool, str]:
    """Check Python version (requires 3.13+)."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major == 3 and version.minor >= 13:
        return True, f"Python 版本: {version_str}"
    else:
        return False, f"Python 版本: {version_str} (需要 3.13+)"


def check_bcrypt_version() -> Tuple[bool, str]:
    """Check bcrypt version (requires < 5.0.0 for passlib compatibility)."""
    try:
        import bcrypt
        version = bcrypt.__version__
        major = int(version.split('.')[0])

        if major < 5:
            return True, f"bcrypt 版本: {version} (兼容)"
        else:
            return False, f"bcrypt 版本: {version} (不兼容 passlib)\n  → 修復: py -3.13 -m pip install \"bcrypt>=4.0.0,<5.0.0\""
    except ImportError:
        return False, "bcrypt 未安裝\n  → 修復: py -3.13 -m pip install -r requirements.txt"
    except AttributeError:
        # bcrypt 5.x may not have __version__
        return False, "bcrypt 版本無法檢測 (可能是 5.x)\n  → 修復: py -3.13 -m pip install \"bcrypt>=4.0.0,<5.0.0\""


def check_passlib_version() -> Tuple[bool, str]:
    """Check passlib installation."""
    try:
        import passlib
        version = getattr(passlib, '__version__', 'unknown')
        return True, f"passlib 版本: {version}"
    except ImportError:
        return False, "passlib 未安裝\n  → 修復: py -3.13 -m pip install passlib[bcrypt]"


def check_agent_framework() -> Tuple[bool, str]:
    """Check agent_framework installation."""
    try:
        import agent_framework
        version = getattr(agent_framework, '__version__', 'installed')
        return True, f"agent_framework: {version}"
    except ImportError:
        return False, "agent_framework 未安裝\n  → 修復: py -3.13 -m pip install -r requirements.txt"


def check_database_connection() -> Tuple[bool, str]:
    """Check database connectivity."""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        from sqlalchemy import create_engine, text

        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            # Build URL from components
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'ipa_platform')
            db_user = os.getenv('DB_USER', 'ipa_user')
            db_password = os.getenv('DB_PASSWORD', 'ipa_password')
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            # Extract PostgreSQL version
            pg_version = version.split(',')[0] if version else 'unknown'
            return True, f"連接成功: {pg_version[:30]}"
    except ImportError as e:
        return False, f"缺少依賴: {e}\n  → 修復: py -3.13 -m pip install sqlalchemy psycopg2-binary python-dotenv"
    except Exception as e:
        return False, f"連接失敗: {str(e)[:50]}\n  → 確保 Docker 服務已啟動: python scripts/dev.py start docker"


def check_users_table_schema() -> Tuple[bool, str]:
    """Check users table has correct schema."""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        from sqlalchemy import create_engine, inspect

        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'ipa_platform')
            db_user = os.getenv('DB_USER', 'ipa_user')
            db_password = os.getenv('DB_PASSWORD', 'ipa_password')
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        engine = create_engine(db_url)
        inspector = inspect(engine)

        # Check if users table exists
        tables = inspector.get_table_names()
        if 'users' not in tables:
            return False, "users 表不存在\n  → 修復: cd backend && py -3.13 -m alembic upgrade head"

        # Check required columns
        columns = {c['name'] for c in inspector.get_columns('users')}
        required_columns = {'id', 'email', 'hashed_password', 'full_name'}
        missing = required_columns - columns

        if missing:
            # Check for old column names
            has_old_names = 'password_hash' in columns or 'name' in columns
            hint = ""
            if has_old_names:
                hint = "\n  → 資料庫使用舊欄位名稱，需要遷移"
            return False, f"users 表缺少欄位: {', '.join(missing)}{hint}\n  → 修復: cd backend && py -3.13 -m alembic upgrade head"

        return True, "users 表結構正確"
    except Exception as e:
        return False, f"檢查失敗: {str(e)[:50]}"


def check_sessions_table() -> Tuple[bool, str]:
    """Check sessions table exists."""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        from sqlalchemy import create_engine, inspect

        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'ipa_platform')
            db_user = os.getenv('DB_USER', 'ipa_user')
            db_password = os.getenv('DB_PASSWORD', 'ipa_password')
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        engine = create_engine(db_url)
        inspector = inspect(engine)

        tables = inspector.get_table_names()
        if 'sessions' in tables:
            return True, "sessions 表存在"
        else:
            return False, "sessions 表不存在\n  → 修復: cd backend && py -3.13 -m alembic upgrade head"
    except Exception as e:
        return False, f"檢查失敗: {str(e)[:50]}"


def check_env_var(name: str, description: str) -> Tuple[bool, str]:
    """Check if an environment variable is set."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    value = os.getenv(name)
    if value:
        # Mask sensitive values
        if 'KEY' in name or 'PASSWORD' in name or 'SECRET' in name:
            display = '***已設定***'
        else:
            display = value[:30] + '...' if len(value) > 30 else value
        return True, f"{name}: {display}"
    else:
        return False, f"{name} 未設定\n  → 在 .env 檔案中設定此變數"


def main() -> int:
    """Main verification function."""
    print("=" * 60)
    print("IPA Platform 環境驗證")
    print("=" * 60)

    errors: List[str] = []

    # Python Environment Checks
    print_section("Python 環境")

    checks = [
        check_python_version(),
        check_bcrypt_version(),
        check_passlib_version(),
        check_agent_framework(),
    ]

    for passed, message in checks:
        if passed:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
            errors.append(message)

    # Database Checks
    print_section("資料庫")

    db_checks = [
        check_database_connection(),
        check_users_table_schema(),
        check_sessions_table(),
    ]

    for passed, message in db_checks:
        if passed:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
            errors.append(message)

    # Environment Variable Checks
    print_section("環境變數")

    env_checks = [
        ('DB_HOST', '資料庫主機'),
        ('AZURE_OPENAI_ENDPOINT', 'Azure OpenAI 端點'),
        ('AZURE_OPENAI_API_KEY', 'Azure OpenAI API 金鑰'),
    ]

    for env_name, desc in env_checks:
        passed, message = check_env_var(env_name, desc)
        if passed:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
            # Don't count env vars as critical errors

    # Summary
    print()
    print("=" * 60)

    if not errors:
        print("驗證結果: 全部通過 ✓")
        print("=" * 60)
        return 0
    else:
        print(f"驗證結果: {len(errors)} 個問題需要修復")
        print("=" * 60)
        print("\n修復建議:")
        for i, error in enumerate(errors, 1):
            print(f"\n{i}. {error.split(chr(10))[0]}")
            # Print hints if available
            lines = error.split('\n')
            for line in lines[1:]:
                print(f"   {line}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
