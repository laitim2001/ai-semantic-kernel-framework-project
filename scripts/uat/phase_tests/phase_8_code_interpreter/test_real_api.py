"""
Phase 8: Code Interpreter - Real API Test (No Simulation)

純真實 API 測試 - 無任何模擬
使用 Azure OpenAI Code Interpreter 進行財務數據分析
"""

import asyncio
import json
import sys
import io
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class CodeInterpreterRealTest:
    """Code Interpreter 真實 API 測試"""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.results: Dict[str, Any] = {}

    async def run_all_tests(self) -> Dict[str, Any]:
        """執行所有測試"""
        print("=" * 60)
        print("Phase 8: Code Interpreter - Real API Test")
        print("=" * 60)

        async with httpx.AsyncClient(timeout=120.0) as client:
            self.client = client

            # Step 1: Health Check
            await self.test_health_check()

            # Step 2: Create Session
            await self.test_create_session()

            # Step 3: Execute Simple Code
            await self.test_execute_simple_code()

            # Step 4: Analyze Financial Data
            await self.test_analyze_financial_data()

            # Step 5: Generate Chart
            await self.test_generate_chart()

            # Step 6: Complex Analysis
            await self.test_complex_analysis()

            # Step 7: Cleanup Session
            await self.test_cleanup_session()

        return self.generate_report()

    async def test_health_check(self):
        """Step 1: 健康檢查"""
        print("\n[Step 1] Health Check")
        print("-" * 40)

        response = await self.client.get(
            f"{self.base_url}/code-interpreter/health"
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Status: {data['status']}")
            print(f"       Azure OpenAI: {'Configured' if data['azure_openai_configured'] else 'Not Configured'}")
            self.results["health_check"] = {"success": True, "data": data}
        else:
            print(f"[FAIL] {response.status_code}")
            self.results["health_check"] = {"success": False, "error": response.text}
            raise Exception("Health check failed")

    async def test_create_session(self):
        """Step 2: 建立會話"""
        print("\n[Step 2] Create Session")
        print("-" * 40)

        response = await self.client.post(
            f"{self.base_url}/code-interpreter/sessions",
            json={
                "name": "Financial Analysis Session",
                "instructions": "You are a financial data analysis assistant skilled in Python data processing and visualization."
            }
        )

        if response.status_code == 201:
            data = response.json()
            self.session_id = data["session"]["session_id"]
            print(f"[PASS] Session created: {self.session_id}")
            self.results["create_session"] = {"success": True, "session_id": self.session_id}
        else:
            print(f"[FAIL] {response.status_code} - {response.text}")
            self.results["create_session"] = {"success": False, "error": response.text}
            raise Exception("Session creation failed")

    async def test_execute_simple_code(self):
        """Step 3: 執行簡單代碼"""
        print("\n[Step 3] Execute Simple Code")
        print("-" * 40)

        code = """
# Simple math calculation
import math

result = {
    "pi": math.pi,
    "sqrt_2": math.sqrt(2),
    "factorial_10": math.factorial(10)
}

print(f"Pi = {result['pi']:.6f}")
print(f"sqrt(2) = {result['sqrt_2']:.6f}")
print(f"10! = {result['factorial_10']}")
result
"""

        response = await self.client.post(
            f"{self.base_url}/code-interpreter/execute",
            json={
                "code": code,
                "session_id": self.session_id,
                "timeout": 60
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Execution success: {data['success']}")
            print(f"       Output: {data['output'][:200]}...")
            print(f"       Time: {data['execution_time']:.2f}s")
            self.results["execute_simple"] = {"success": data['success'], "data": data}
        else:
            print(f"[FAIL] {response.status_code} - {response.text}")
            self.results["execute_simple"] = {"success": False, "error": response.text}

    async def test_analyze_financial_data(self):
        """Step 4: 分析財務數據"""
        print("\n[Step 4] Analyze Financial Data")
        print("-" * 40)

        task = """
Please analyze the following Q4 sales data:

Month,Sales,Cost,Profit
October,1250000,875000,375000
November,1380000,966000,414000
December,1620000,1134000,486000

Calculate:
1. Total sales, total cost, total profit
2. Average profit margin
3. Month-over-month growth rate
4. Forecast next month's sales (linear regression)
"""

        response = await self.client.post(
            f"{self.base_url}/code-interpreter/analyze",
            json={
                "task": task,
                "session_id": self.session_id,
                "timeout": 90
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Analysis success: {data['success']}")
            print(f"       Output preview:")
            output = data.get('output', '')
            for line in output[:500].split('\n')[:10]:
                print(f"       {line}")
            if len(output) > 500:
                print("       ...")
            self.results["analyze_financial"] = {"success": data['success'], "data": data}
        else:
            print(f"[FAIL] {response.status_code} - {response.text}")
            self.results["analyze_financial"] = {"success": False, "error": response.text}

    async def test_generate_chart(self):
        """Step 5: 生成圖表"""
        print("\n[Step 5] Generate Chart")
        print("-" * 40)

        task = """
Create a combined bar and line chart for sales data using matplotlib:

Data:
- Months: ['October', 'November', 'December']
- Sales: [1250000, 1380000, 1620000]
- Profit: [375000, 414000, 486000]

Requirements:
1. Bar chart for sales
2. Line chart for profit trend
3. Add data labels
4. Use professional styling
"""

        response = await self.client.post(
            f"{self.base_url}/code-interpreter/analyze",
            json={
                "task": task,
                "session_id": self.session_id,
                "timeout": 90
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Chart generation: {data['success']}")
            files = data.get('files', [])
            if files:
                print(f"       Generated files: {len(files)}")
                for f in files:
                    print(f"       - {f.get('filename', f.get('file_id', 'unknown'))}")
            else:
                print("       No files generated (chart may be displayed inline)")
            self.results["generate_chart"] = {"success": data['success'], "data": data}
        else:
            print(f"[FAIL] {response.status_code} - {response.text}")
            self.results["generate_chart"] = {"success": False, "error": response.text}

    async def test_complex_analysis(self):
        """Step 6: 複雜分析任務"""
        print("\n[Step 6] Complex Analysis")
        print("-" * 40)

        task = """
Perform a complete financial report analysis:

1. Create a DataFrame with these metrics:
   - Month, Sales, Cost, Profit, Profit Margin, MoM Growth Rate

2. Perform statistical analysis:
   - Descriptive statistics (mean, std, min, max)
   - Correlation analysis (sales vs profit)

3. Generate analysis summary

Data:
October: Sales 1,250,000, Cost 875,000
November: Sales 1,380,000, Cost 966,000
December: Sales 1,620,000, Cost 1,134,000
"""

        response = await self.client.post(
            f"{self.base_url}/code-interpreter/analyze",
            json={
                "task": task,
                "session_id": self.session_id,
                "timeout": 120
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Complex analysis: {data['success']}")
            output = data.get('output', '')
            print(f"       Output preview:")
            for line in output[:600].split('\n')[:15]:
                print(f"       {line}")
            if len(output) > 600:
                print("       ...")
            self.results["complex_analysis"] = {"success": data['success'], "data": data}
        else:
            print(f"[FAIL] {response.status_code} - {response.text}")
            self.results["complex_analysis"] = {"success": False, "error": response.text}

    async def test_cleanup_session(self):
        """Step 7: 清理會話"""
        print("\n[Step 7] Cleanup Session")
        print("-" * 40)

        if not self.session_id:
            print("[SKIP] No session to cleanup")
            self.results["cleanup"] = {"success": True, "skipped": True}
            return

        response = await self.client.delete(
            f"{self.base_url}/code-interpreter/sessions/{self.session_id}"
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[PASS] Session cleanup: {data['success']}")
            self.results["cleanup"] = {"success": True, "data": data}
        else:
            print(f"[WARN] Cleanup response: {response.status_code} - {response.text}")
            self.results["cleanup"] = {"success": False, "error": response.text}

    def generate_report(self) -> Dict[str, Any]:
        """生成測試報告"""
        print("\n" + "=" * 60)
        print("TEST REPORT")
        print("=" * 60)

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r.get("success"))

        print(f"\nResults: {passed_tests}/{total_tests} tests passed")
        print(f"Success rate: {(passed_tests/total_tests*100):.1f}%")

        print("\nTest Details:")
        for test_name, result in self.results.items():
            status = "[PASS]" if result.get("success") else "[FAIL]"
            print(f"  {status} {test_name}")
            if not result.get("success") and result.get("error"):
                error_text = result['error'][:100] if isinstance(result['error'], str) else str(result['error'])[:100]
                print(f"         Error: {error_text}...")

        report = {
            "phase": 8,
            "scenario": "Code Interpreter - Financial Analysis",
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": f"{(passed_tests/total_tests*100):.1f}%",
            "overall_success": passed_tests == total_tests,
            "test_results": self.results
        }

        # 保存報告
        output_file = f"phase_8_real_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nReport saved to: {output_file}")

        return report


async def main():
    """主函數"""
    test = CodeInterpreterRealTest()
    report = await test.run_all_tests()

    print("\n" + "=" * 60)
    if report["overall_success"]:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    return report


if __name__ == "__main__":
    asyncio.run(main())
