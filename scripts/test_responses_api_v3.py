"""
Test Azure OpenAI Responses API with api-version 2025-03-01-preview

Fixed version:
1. Proper encoding handling for Chinese output
2. Correct Responses API parameters with container
3. Save all results to files
"""

import os
import sys
import io
import warnings
from datetime import datetime
from pathlib import Path

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def safe_print(text: str):
    """Print text safely, handling encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('utf-8', errors='replace').decode('utf-8'))


def get_client():
    from openai import AzureOpenAI
    return AzureOpenAI(
        api_version=AZURE_CONFIG["api_version"],
        azure_endpoint=AZURE_CONFIG["azure_endpoint"],
        api_key=AZURE_CONFIG["subscription_key"],
    )


def test_chat_completion(client):
    """Test: Basic chat completion."""
    print_section("Test 1: Chat Completion")

    try:
        response = client.chat.completions.create(
            model=AZURE_CONFIG["deployment"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 100 + 200? Reply with just the number."}
            ],
            max_completion_tokens=50,
        )

        answer = response.choices[0].message.content.strip()
        print(f"[OK] Chat completion successful")
        print(f"    Model: {response.model}")
        print(f"    Question: 100 + 200 = ?")
        print(f"    Answer: {answer}")
        return True

    except Exception as e:
        print(f"[ERROR] Chat completion failed: {e}")
        return False


def test_responses_api_simple(client):
    """Test: Simple Responses API without tools."""
    print_section("Test 2: Responses API (Simple)")

    print(f"API Version: {AZURE_CONFIG['api_version']}")

    try:
        response = client.responses.create(
            model=AZURE_CONFIG["deployment"],
            input="Calculate 25 * 48. Just give the result number.",
        )

        print(f"[OK] Responses API successful!")
        print(f"    Response ID: {response.id}")

        # Get output
        if hasattr(response, 'output_text'):
            print(f"    Result: {response.output_text}")
        elif hasattr(response, 'output'):
            for item in response.output:
                if hasattr(item, 'content'):
                    for c in item.content:
                        if hasattr(c, 'text'):
                            print(f"    Result: {c.text}")

        return True

    except Exception as e:
        print(f"[ERROR] Responses API failed: {e}")
        return False


def test_responses_api_with_code(client):
    """Test: Responses API with code_interpreter (with container)."""
    print_section("Test 3: Responses API + Code Interpreter")

    try:
        # The new Responses API requires container configuration for code_interpreter
        response = client.responses.create(
            model=AZURE_CONFIG["deployment"],
            input="Write Python code to calculate the sum of squares from 1 to 10, then print the result.",
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto"  # Let Azure manage the container
                }
            }],
        )

        print(f"[OK] Responses API with code_interpreter successful!")
        print(f"    Response ID: {response.id}")

        # Parse output
        if hasattr(response, 'output'):
            for item in response.output:
                if hasattr(item, 'type'):
                    print(f"    Output type: {item.type}")
                    if item.type == 'code_interpreter_call':
                        if hasattr(item, 'code'):
                            print(f"    Code executed:\n{item.code}")
                    elif hasattr(item, 'content'):
                        for c in item.content:
                            if hasattr(c, 'text'):
                                print(f"    Text: {c.text}")

        return True

    except Exception as e:
        print(f"[INFO] Responses API with code_interpreter: {e}")
        print("       Note: Container configuration may vary by region/deployment")
        return False


def test_upload_and_analyze_excel(client):
    """Test: Upload Excel file and analyze using Assistants API."""
    print_section("Test 4: Upload & Analyze Excel File")

    OUTPUT_DIR.mkdir(exist_ok=True)
    assistant = None
    uploaded_file = None

    if not TEST_EXCEL_FILE.exists():
        print(f"[ERROR] File not found: {TEST_EXCEL_FILE}")
        return False

    print(f"[INFO] File: {TEST_EXCEL_FILE.name}")
    print(f"       Size: {TEST_EXCEL_FILE.stat().st_size:,} bytes")

    try:
        # Upload file
        print("\n[INFO] Uploading to Azure...")
        with open(TEST_EXCEL_FILE, 'rb') as f:
            uploaded_file = client.files.create(file=f, purpose="assistants")

        print(f"[OK] Uploaded: {uploaded_file.id}")

        # Create assistant
        print("[INFO] Creating analyst assistant...")
        assistant = client.beta.assistants.create(
            name="Excel Analyst",
            instructions="""You are a data analyst. Analyze Excel files and provide:
1. File structure (sheets, columns, rows)
2. Data summary and statistics
3. Key findings and patterns
4. Create charts if useful

Respond in Traditional Chinese.""",
            model=AZURE_CONFIG["deployment"],
            tools=[{"type": "code_interpreter"}],
        )
        print(f"[OK] Assistant: {assistant.id}")

        # Create thread and message
        thread = client.beta.threads.create()
        print(f"[OK] Thread: {thread.id}")

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="""Please analyze this Excel file (DCE_feature_list_update_20251214_v1.xlsx):

1. What sheets are in this file?
2. What are the main columns?
3. How many features/rows are there?
4. List the top 10 most important features
5. Create a summary chart if appropriate

Respond in Traditional Chinese (繁體中文).""",
            attachments=[{
                "file_id": uploaded_file.id,
                "tools": [{"type": "code_interpreter"}]
            }]
        )
        print(f"[OK] Message: {message.id}")

        # Run
        print("\n[INFO] Running analysis (1-2 minutes)...")
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            timeout=180,
        )
        print(f"[OK] Run status: {run.status}")

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)

            # Collect results
            analysis_text = ""
            image_files = []

            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "text":
                            analysis_text += content.text.value + "\n\n"
                        elif content.type == "image_file":
                            image_files.append(content.image_file.file_id)

            # Save analysis to file
            result_file = OUTPUT_DIR / "dce_analysis_result.md"
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write("# DCE Feature List Analysis Report\n\n")
                f.write(f"**Analysis Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**Source File**: {TEST_EXCEL_FILE.name}\n\n")
                f.write("---\n\n")
                f.write(analysis_text)

            print(f"\n[OK] Analysis saved to: {result_file}")

            # Download images
            for i, file_id in enumerate(image_files, 1):
                try:
                    content = client.files.content(file_id)
                    img_path = OUTPUT_DIR / f"dce_chart_{i}.png"
                    with open(img_path, 'wb') as f:
                        f.write(content.read())
                    print(f"[OK] Chart saved: {img_path}")
                except Exception as e:
                    print(f"[WARN] Could not download chart {i}: {e}")

            # Print preview
            print("\n" + "="*70)
            print("  Analysis Preview (first 2000 chars)")
            print("="*70)
            preview = analysis_text[:2000]
            safe_print(preview)
            if len(analysis_text) > 2000:
                print("\n... [See full results in dce_analysis_result.md]")

            return True

        else:
            print(f"[ERROR] Run failed: {run.status}")
            return False

    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if uploaded_file:
            try:
                client.files.delete(uploaded_file.id)
                print(f"\n[CLEANUP] Deleted file: {uploaded_file.id}")
            except:
                pass
        if assistant:
            try:
                client.beta.assistants.delete(assistant.id)
                print(f"[CLEANUP] Deleted assistant: {assistant.id}")
            except:
                pass


def main():
    print("\n" + "="*70)
    print("  Azure AI Foundry - Responses API & Excel Analysis")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  API Version: " + AZURE_CONFIG["api_version"])
    print("="*70)

    client = get_client()
    print(f"\n[OK] Client created")
    print(f"    Endpoint: {AZURE_CONFIG['azure_endpoint']}")

    results = {}

    # Test 1: Chat
    results["chat_completion"] = test_chat_completion(client)

    # Test 2: Simple Responses API
    results["responses_api_simple"] = test_responses_api_simple(client)

    # Test 3: Responses API + Code Interpreter
    results["responses_api_code"] = test_responses_api_with_code(client)

    # Test 4: Excel Analysis
    results["excel_analysis"] = test_upload_and_analyze_excel(client)

    # Summary
    print_section("Test Summary")

    for name, passed in results.items():
        icon = "[OK]" if passed else "[X]"
        status = "PASSED" if passed else "FAILED"
        print(f"  {icon} {name}: {status}")

    print(f"\n  Output: {OUTPUT_DIR.absolute()}")

    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.glob("dce_*"))
        if files:
            print(f"\n  Generated files:")
            for f in files:
                print(f"    - {f.name} ({f.stat().st_size:,} bytes)")

    passed = sum(1 for v in results.values() if v)
    print(f"\n  Total: {passed}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
