"""
Phase 8: Code Interpreter - Responses API Test

Tests Code Interpreter functionality using Responses API (api-version >= 2025-03-01-preview)
Shows execution process including:
- The actual Python code executed by AI
- Step-by-step outputs and logs
- Generated files/images

No simulation - real Azure OpenAI API calls only.
"""

import sys
import io
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import httpx

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 120.0


def print_separator(title: str = ""):
    """Print a separator line."""
    if title:
        print(f"\n{'='*60}")
        print(f" {title}")
        print('='*60)
    else:
        print('-'*40)


def print_execution_steps(response_data: Dict[str, Any]):
    """Parse and display execution steps from Responses API."""
    print("\n[Execution Process]")
    print_separator()

    metadata = response_data.get("metadata", {})
    code_outputs = metadata.get("code_outputs", [])

    if code_outputs:
        for i, code_item in enumerate(code_outputs, 1):
            print(f"\n  Step {i}:")
            print(f"  {'~'*50}")

            # Show the code that was executed (FULL - no truncation)
            code = code_item.get("code", "")
            if code:
                print(f"  [Code Executed]")
                for line in code.split('\n'):
                    print(f"    {line}")

            # Show code ID
            code_id = code_item.get("id", "")
            if code_id:
                print(f"  [Call ID]: {code_id}")
    else:
        print("  (No code execution steps captured)")

    print_separator()


async def test_health_check(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Step 1: Health check."""
    print("\n[Step 1] Health Check - Responses API")
    print_separator()

    try:
        response = await client.get(f"{BASE_URL}/api/v1/code-interpreter/health")
        data = response.json()

        if response.status_code == 200:
            print(f"[PASS] Status: {data.get('status')}")
            print(f"       Azure OpenAI: {'Configured' if data.get('azure_openai_configured') else 'Not configured'}")
            return {"status": "pass", "data": data}
        else:
            print(f"[FAIL] HTTP {response.status_code}")
            return {"status": "fail", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return {"status": "fail", "error": str(e)}


async def test_responses_api_execute(client: httpx.AsyncClient, session_id: str) -> Dict[str, Any]:
    """Step 2: Execute code with Responses API showing execution process."""
    print("\n[Step 2] Execute Code (Responses API)")
    print_separator()

    code = '''
import math

# Calculate various mathematical results
results = {
    "pi": math.pi,
    "e": math.e,
    "golden_ratio": (1 + math.sqrt(5)) / 2,
    "factorial_10": math.factorial(10),
    "log2_1024": math.log2(1024)
}

# Print results
for key, value in results.items():
    print(f"{key}: {value}")

results
'''

    try:
        print(f"  Sending code to execute...")
        print(f"  Session: {session_id}")

        response = await client.post(
            f"{BASE_URL}/api/v1/code-interpreter/execute",
            json={
                "session_id": session_id,
                "code": code,
                "api_mode": "responses",  # Force Responses API
            },
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            success = data.get("success", False)

            if success:
                print(f"[PASS] Execution success!")
                print(f"       Time: {data.get('execution_time', 0):.2f}s")
                print(f"       API Mode: {data.get('metadata', {}).get('api_mode', 'unknown')}")

                # Show execution process
                print_execution_steps(data)

                # Show output
                print("\n[Output]")
                output = data.get("output", "")
                print(f"  {output[:500]}..." if len(output) > 500 else f"  {output}")

                return {"status": "pass", "data": data}
            else:
                print(f"[FAIL] Execution failed: {data.get('error')}")
                return {"status": "fail", "error": data.get("error")}
        else:
            error_msg = response.text[:200]
            print(f"[FAIL] HTTP {response.status_code} - {error_msg}")
            return {"status": "fail", "error": error_msg}

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return {"status": "fail", "error": str(e)}


async def test_responses_api_analyze(client: httpx.AsyncClient, session_id: str) -> Dict[str, Any]:
    """Step 3: Analyze data with Responses API showing AI-generated code."""
    print("\n[Step 3] Analyze Data (AI Generates Code)")
    print_separator()

    task = """
    Analyze this sales data and provide insights:

    Q1_2024 = {"Jan": 150000, "Feb": 165000, "Mar": 180000}
    Q2_2024 = {"Apr": 175000, "May": 190000, "Jun": 205000}

    Calculate:
    1. Total revenue per quarter
    2. Month-over-month growth rate
    3. Average monthly revenue
    4. Best performing month
    """

    try:
        print(f"  Sending analysis task...")
        print(f"  Task: Analyze sales data")

        response = await client.post(
            f"{BASE_URL}/api/v1/code-interpreter/analyze",
            json={
                "session_id": session_id,
                "task": task,
                "api_mode": "responses",
            },
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            success = data.get("success", False)

            if success:
                print(f"[PASS] Analysis complete!")
                print(f"       Time: {data.get('execution_time', 0):.2f}s")

                # Show execution process - this shows what code AI wrote
                print_execution_steps(data)

                # Show analysis results
                print("\n[Analysis Results]")
                output = data.get("output", "")
                # Show first 800 chars
                print(f"  {output[:800]}..." if len(output) > 800 else f"  {output}")

                return {"status": "pass", "data": data}
            else:
                print(f"[FAIL] Analysis failed: {data.get('error')}")
                return {"status": "fail", "error": data.get("error")}
        else:
            error_msg = response.text[:200]
            print(f"[FAIL] HTTP {response.status_code} - {error_msg}")
            return {"status": "fail", "error": error_msg}

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return {"status": "fail", "error": str(e)}


async def test_responses_api_chart(client: httpx.AsyncClient, session_id: str) -> Dict[str, Any]:
    """Step 4: Generate chart with Responses API."""
    print("\n[Step 4] Generate Chart (Responses API)")
    print_separator()

    code = '''
import matplotlib.pyplot as plt
import numpy as np

# Create sample data
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
revenue = [150000, 165000, 180000, 175000, 190000, 205000]

# Create bar chart
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(months, revenue, color='steelblue', edgecolor='navy')

# Add value labels on bars
for bar, val in zip(bars, revenue):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2000,
            f'${val:,}', ha='center', va='bottom', fontsize=10)

ax.set_xlabel('Month')
ax.set_ylabel('Revenue ($)')
ax.set_title('Monthly Revenue - H1 2024')
ax.set_ylim(0, 230000)

plt.tight_layout()
plt.savefig('revenue_chart.png', dpi=100)
plt.show()
print("Chart generated successfully!")
'''

    try:
        print(f"  Generating chart...")

        response = await client.post(
            f"{BASE_URL}/api/v1/code-interpreter/execute",
            json={
                "session_id": session_id,
                "code": code,
                "api_mode": "responses",
            },
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            success = data.get("success", False)

            if success:
                files = data.get("files", [])
                print(f"[PASS] Chart generation complete!")
                print(f"       Time: {data.get('execution_time', 0):.2f}s")
                print(f"       Files generated: {len(files)}")

                # Show execution process
                print_execution_steps(data)

                if files:
                    print("\n[Generated Files]")
                    for f in files:
                        print(f"  - Type: {f.get('type')}, File ID: {f.get('file_id', 'N/A')}")

                return {"status": "pass", "data": data}
            else:
                print(f"[FAIL] Chart generation failed: {data.get('error')}")
                return {"status": "fail", "error": data.get("error")}
        else:
            error_msg = response.text[:200]
            print(f"[FAIL] HTTP {response.status_code} - {error_msg}")
            return {"status": "fail", "error": error_msg}

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return {"status": "fail", "error": str(e)}


async def test_create_session(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Create a test session."""
    print("\n[Setup] Create Session")
    print_separator()

    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/code-interpreter/sessions",
            json={"name": "responses_api_test"}
        )

        if response.status_code in (200, 201):
            data = response.json()
            # Session ID is nested under "session" key
            session_data = data.get("session", {})
            session_id = session_data.get("session_id")
            print(f"[PASS] Session created: {session_id}")
            return {"status": "pass", "session_id": session_id}
        else:
            print(f"[FAIL] HTTP {response.status_code}")
            return {"status": "fail", "error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return {"status": "fail", "error": str(e)}


async def test_cleanup_session(client: httpx.AsyncClient, session_id: str) -> Dict[str, Any]:
    """Cleanup session."""
    print("\n[Cleanup] Delete Session")
    print_separator()

    try:
        response = await client.delete(
            f"{BASE_URL}/api/v1/code-interpreter/sessions/{session_id}"
        )

        if response.status_code == 200:
            print(f"[PASS] Session cleaned up")
            return {"status": "pass"}
        else:
            print(f"[WARN] Cleanup returned {response.status_code}")
            return {"status": "pass"}  # Don't fail test on cleanup issues
    except Exception as e:
        print(f"[WARN] Cleanup error: {e}")
        return {"status": "pass"}


async def run_tests():
    """Run all Responses API tests."""
    print_separator("Phase 8: Code Interpreter - Responses API Test")
    print(f"API Version: 2025-03-01-preview")
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}
    session_id = None

    async with httpx.AsyncClient() as client:
        # Health check
        results["health_check"] = await test_health_check(client)

        if results["health_check"]["status"] != "pass":
            print("\n[ABORT] Health check failed. Cannot continue.")
            return results

        # Create session
        session_result = await test_create_session(client)
        results["create_session"] = session_result

        if session_result["status"] != "pass":
            print("\n[ABORT] Session creation failed. Cannot continue.")
            return results

        session_id = session_result["session_id"]

        # Test Responses API
        results["execute_code"] = await test_responses_api_execute(client, session_id)
        results["analyze_data"] = await test_responses_api_analyze(client, session_id)
        results["generate_chart"] = await test_responses_api_chart(client, session_id)

        # Cleanup
        results["cleanup"] = await test_cleanup_session(client, session_id)

    return results


def print_report(results: Dict[str, Any]):
    """Print test report."""
    print_separator("TEST REPORT")

    passed = sum(1 for r in results.values() if r.get("status") == "pass")
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed")
    print(f"Success rate: {passed/total*100:.1f}%")

    print("\nTest Details:")
    for name, result in results.items():
        status = "[PASS]" if result.get("status") == "pass" else "[FAIL]"
        print(f"  {status} {name}")
        if result.get("status") != "pass" and result.get("error"):
            print(f"         Error: {result.get('error')[:80]}...")

    # Save report
    report_file = f"phase_8_responses_api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "api_version": "2025-03-01-preview",
            "results": {k: {"status": v.get("status"), "error": v.get("error")} for k, v in results.items()},
            "summary": {"passed": passed, "total": total, "rate": passed/total}
        }, f, indent=2)
    print(f"\nReport saved to: {report_file}")

    print_separator()
    if passed == total:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print_separator()


if __name__ == "__main__":
    results = asyncio.run(run_tests())
    print_report(results)
