#!/usr/bin/env python
"""
Test Claude API Key directly with Anthropic API.

This script verifies that the ANTHROPIC_API_KEY in .env is valid
and can successfully communicate with the Claude API.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Load .env from backend directory
from dotenv import load_dotenv
env_path = backend_path / ".env"
load_dotenv(env_path)


def test_api_key_format():
    """Test that API key exists and has valid format."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    print("=" * 60)
    print("Claude API Key Validation Test")
    print("=" * 60)
    print(f"API Key loaded from: {env_path}")
    print(f"API Key exists: {bool(api_key)}")

    if not api_key:
        print("[FAIL] ANTHROPIC_API_KEY not found in environment")
        return False

    # Check format (sk-ant-api03-...)
    if not api_key.startswith("sk-ant-"):
        print(f"[WARN] API Key format unusual: {api_key[:15]}...")

    print(f"API Key prefix: {api_key[:20]}...")
    print(f"API Key length: {len(api_key)} characters")
    print("[OK] API Key format looks valid")
    return True


def test_direct_api_call():
    """Test direct API call to Claude."""
    try:
        import anthropic
    except ImportError:
        print("[INFO] Installing anthropic package...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
        import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[SKIP] No API key available")
        return False

    print("\n" + "=" * 60)
    print("Direct Claude API Call Test")
    print("=" * 60)

    try:
        client = anthropic.Anthropic(api_key=api_key)

        print("Sending test message to Claude...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'API key is valid' in one line."}
            ]
        )

        if response.content:
            text = response.content[0].text
            print(f"[OK] Claude responded: {text}")
            print(f"Model: {response.model}")
            print(f"Usage: input={response.usage.input_tokens}, output={response.usage.output_tokens}")
            return True
        else:
            print("[FAIL] Empty response from Claude")
            return False

    except anthropic.AuthenticationError as e:
        print(f"[FAIL] Authentication error: {e}")
        return False
    except anthropic.APIError as e:
        print(f"[FAIL] API error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False


def main():
    """Run all tests."""
    results = []

    # Test 1: API key format
    results.append(("API Key Format", test_api_key_format()))

    # Test 2: Direct API call
    results.append(("Direct API Call", test_direct_api_call()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] Claude API key is valid and working!")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Check API key configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
