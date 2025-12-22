"""
Test Azure OpenAI Responses API with api-version 2025-03-01-preview

Tests:
1. Responses API with code_interpreter
2. Upload and analyze Excel file (DCE_feature_list_update_20251214_v1.xlsx)
3. Download generated analysis results
"""

import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Azure AI Foundry Configuration - Load from environment variables
AZURE_CONFIG = {
    "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2025-03-01-preview"),
    "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
    "subscription_key": os.environ.get("AZURE_OPENAI_API_KEY", ""),
}

# Test file path
TEST_EXCEL_FILE = Path(r"C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project\claudedocs\uat\sample-file\DCE_feature_list_update_20251214_v1.xlsx")

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def get_client():
    """Create Azure OpenAI client with new API version."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_version=AZURE_CONFIG["api_version"],
        azure_endpoint=AZURE_CONFIG["azure_endpoint"],
        api_key=AZURE_CONFIG["subscription_key"],
    )
    return client


def test_responses_api(client):
    """Test 1: Responses API with code_interpreter."""
    print_section("Test 1: Responses API (api-version 2025-03-01-preview)")

    print(f"API Version: {AZURE_CONFIG['api_version']}")
    print(f"Deployment: {AZURE_CONFIG['deployment']}")

    try:
        # Check if Responses API exists
        if not hasattr(client, 'responses'):
            print("[ERROR] Responses API not found in client")
            print("        Make sure you have the latest openai package: pip install -U openai")
            return False

        print("[INFO] Testing Responses API with code_interpreter...")

        response = client.responses.create(
            model=AZURE_CONFIG["deployment"],
            input="Calculate the sum of squares from 1 to 10 using Python. Show the code and result.",
            tools=[{"type": "code_interpreter"}],
        )

        print(f"[OK] Responses API call successful!")
        print(f"    Response ID: {response.id}")
        print(f"    Status: {response.status}")

        # Extract output
        if hasattr(response, 'output') and response.output:
            print(f"\n--- Response Output ---")
            for item in response.output:
                if hasattr(item, 'type'):
                    if item.type == 'message':
                        for content in item.content:
                            if hasattr(content, 'text'):
                                print(content.text)
                    elif item.type == 'code_interpreter_call':
                        print(f"[Code Interpreter] ID: {item.id}")
                        if hasattr(item, 'code'):
                            print(f"Code:\n{item.code}")

        return True

    except Exception as e:
        print(f"[ERROR] Responses API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_responses_api_simple(client):
    """Test 1b: Simple Responses API without tools."""
    print_section("Test 1b: Simple Responses API (no tools)")

    try:
        response = client.responses.create(
            model=AZURE_CONFIG["deployment"],
            input="What is 15 * 23? Just give me the number.",
        )

        print(f"[OK] Simple Responses API call successful!")
        print(f"    Response ID: {response.id}")

        # Try to get the output text
        if hasattr(response, 'output_text'):
            print(f"    Output: {response.output_text}")
        elif hasattr(response, 'output'):
            print(f"    Output: {response.output}")

        return True

    except Exception as e:
        print(f"[INFO] Simple Responses API: {e}")
        return False


def test_upload_excel_assistants_api(client):
    """Test 2: Upload Excel file and analyze using Assistants API (fallback)."""
    print_section("Test 2: Upload & Analyze Excel File (Assistants API)")

    OUTPUT_DIR.mkdir(exist_ok=True)
    assistant = None
    thread = None
    uploaded_file = None

    # Check if file exists
    if not TEST_EXCEL_FILE.exists():
        print(f"[ERROR] Test file not found: {TEST_EXCEL_FILE}")
        return False

    print(f"[INFO] Test file: {TEST_EXCEL_FILE.name}")
    print(f"       Size: {TEST_EXCEL_FILE.stat().st_size:,} bytes")

    try:
        # Upload the Excel file
        print("\n[INFO] Uploading Excel file to Azure...")
        with open(TEST_EXCEL_FILE, 'rb') as f:
            uploaded_file = client.files.create(
                file=f,
                purpose="assistants"
            )

        print(f"[OK] File uploaded successfully!")
        print(f"    Azure File ID: {uploaded_file.id}")
        print(f"    Filename: {uploaded_file.filename}")
        print(f"    Size: {uploaded_file.bytes:,} bytes")

        # Create assistant with code interpreter
        print("\n[INFO] Creating data analysis assistant...")
        assistant = client.beta.assistants.create(
            name="Excel Data Analyst",
            instructions="""You are an expert data analyst. When analyzing Excel files:
1. First, read and understand the structure of the file
2. Provide a summary of the data (columns, rows, data types)
3. Identify key features or patterns
4. Create visualizations if appropriate
5. Provide insights and recommendations

Always respond in Traditional Chinese (繁體中文) for better understanding.""",
            model=AZURE_CONFIG["deployment"],
            tools=[{"type": "code_interpreter"}],
        )
        print(f"[OK] Assistant created: {assistant.id}")

        # Create thread
        thread = client.beta.threads.create()
        print(f"[OK] Thread created: {thread.id}")

        # Create analysis request message
        analysis_prompt = """請分析這個 Excel 文件 (DCE_feature_list_update_20251214_v1.xlsx):

1. **文件結構概覽**：
   - 有多少個工作表 (sheets)?
   - 每個工作表有多少行和列?
   - 主要欄位名稱是什麼?

2. **數據內容分析**：
   - 這個文件記錄的是什麼類型的數據?
   - 有哪些主要的功能特性 (features)?
   - 數據的完整性如何?

3. **關鍵發現**：
   - 列出最重要的 10 個功能特性
   - 如果有狀態欄位，統計各狀態的數量

4. **視覺化**：
   - 如果適合，請創建一個圖表來展示數據分布

請用繁體中文回答，並提供詳細的分析結果。"""

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=analysis_prompt,
            attachments=[{
                "file_id": uploaded_file.id,
                "tools": [{"type": "code_interpreter"}]
            }]
        )
        print(f"[OK] Analysis request sent: {message.id}")

        # Run the assistant
        print("\n[INFO] Running analysis (this may take 1-2 minutes)...")
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            timeout=180,  # 3 minutes timeout
        )

        print(f"[OK] Run completed: {run.status}")

        if run.status == "completed":
            # Get all messages
            messages = client.beta.threads.messages.list(thread_id=thread.id)

            print("\n" + "="*70)
            print("  分析結果 (Analysis Results)")
            print("="*70 + "\n")

            analysis_result = ""
            image_count = 0

            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "text":
                            text = content.text.value
                            analysis_result += text + "\n"
                            print(text)
                            print("-" * 50)

                        elif content.type == "image_file":
                            image_count += 1
                            file_id = content.image_file.file_id
                            print(f"\n[圖表 {image_count}] File ID: {file_id}")

                            # Download the image
                            try:
                                file_content = client.files.content(file_id)
                                image_path = OUTPUT_DIR / f"dce_analysis_chart_{image_count}.png"
                                with open(image_path, 'wb') as f:
                                    f.write(file_content.read())
                                print(f"    已下載到: {image_path}")
                            except Exception as e:
                                print(f"    下載失敗: {e}")

            # Save analysis result to file
            result_file = OUTPUT_DIR / "dce_analysis_result.md"
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(f"# DCE Feature List 分析報告\n\n")
                f.write(f"**分析時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**來源文件**: {TEST_EXCEL_FILE.name}\n\n")
                f.write("---\n\n")
                f.write(analysis_result)

            print(f"\n[OK] 分析結果已保存到: {result_file}")
            print(f"[OK] 共生成 {image_count} 個圖表")

            return True

        else:
            print(f"[ERROR] Run failed: {run.status}")
            if run.last_error:
                print(f"    Error: {run.last_error}")
            return False

    except Exception as e:
        print(f"[ERROR] Excel analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if uploaded_file:
            try:
                client.files.delete(uploaded_file.id)
                print(f"\n[CLEANUP] Deleted uploaded file: {uploaded_file.id}")
            except:
                pass
        if assistant:
            try:
                client.beta.assistants.delete(assistant.id)
                print(f"[CLEANUP] Deleted assistant: {assistant.id}")
            except:
                pass


def test_chat_completion(client):
    """Test 3: Basic chat completion to verify connection."""
    print_section("Test 3: Chat Completion (Connection Verify)")

    try:
        response = client.chat.completions.create(
            model=AZURE_CONFIG["deployment"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Connection successful!' in Traditional Chinese."}
            ],
            max_completion_tokens=50,
        )

        answer = response.choices[0].message.content.strip()
        print(f"[OK] Chat completion successful")
        print(f"    Model: {response.model}")
        print(f"    Response: {answer}")

        return True

    except Exception as e:
        print(f"[ERROR] Chat completion failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  Azure AI Foundry - Responses API & Excel Analysis Test")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  API Version: " + AZURE_CONFIG["api_version"])
    print("="*70)

    client = get_client()
    print(f"\n[OK] Azure OpenAI client created")
    print(f"    Endpoint: {AZURE_CONFIG['azure_endpoint']}")
    print(f"    API Version: {AZURE_CONFIG['api_version']}")

    results = {}

    # Test 3: Chat completion first (verify connection)
    results["chat_completion"] = test_chat_completion(client)

    # Test 1: Responses API
    results["responses_api"] = test_responses_api(client)

    # Test 1b: Simple Responses API
    if not results["responses_api"]:
        results["responses_api_simple"] = test_responses_api_simple(client)

    # Test 2: Upload and analyze Excel file
    results["excel_analysis"] = test_upload_excel_assistants_api(client)

    # Summary
    print_section("Test Summary")

    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        icon = "[OK]" if passed else "[X]"
        print(f"  {icon} {test_name}: {status}")

    print(f"\n  Output directory: {OUTPUT_DIR.absolute()}")

    # List output files
    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.glob("dce_*"))
        if files:
            print(f"\n  Generated files:")
            for f in files:
                print(f"    - {f.name} ({f.stat().st_size:,} bytes)")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n  Total: {passed}/{total} tests passed")


if __name__ == "__main__":
    main()
