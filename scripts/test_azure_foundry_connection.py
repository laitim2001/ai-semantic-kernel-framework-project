"""
Test Azure AI Foundry Project Connection and Code Interpreter

Tests:
1. Azure OpenAI basic connection
2. Chat completion
3. Code Interpreter functionality
"""

import os
import sys
import json
from datetime import datetime

# Azure AI Foundry Configuration - Load from environment variables
AZURE_CONFIG = {
    "tenant_id": os.environ.get("AZURE_TENANT_ID", ""),
    "project_url": os.environ.get("AZURE_AI_PROJECT_URL", ""),
    "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
    "subscription_key": os.environ.get("AZURE_OPENAI_API_KEY", ""),
}


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_openai_connection():
    """Test 1: Basic Azure OpenAI Connection"""
    print_section("Test 1: Azure OpenAI Connection")

    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_version=AZURE_CONFIG["api_version"],
            azure_endpoint=AZURE_CONFIG["azure_endpoint"],
            api_key=AZURE_CONFIG["subscription_key"],
        )

        print(f"[OK] AzureOpenAI client created")
        print(f"    Endpoint: {AZURE_CONFIG['azure_endpoint']}")
        print(f"    API Version: {AZURE_CONFIG['api_version']}")
        print(f"    Deployment: {AZURE_CONFIG['deployment']}")

        return client

    except ImportError:
        print("[ERROR] openai package not installed")
        print("        Run: pip install openai")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create client: {e}")
        return None


def test_chat_completion(client):
    """Test 2: Chat Completion"""
    print_section("Test 2: Chat Completion")

    if not client:
        print("[SKIP] No client available")
        return False

    try:
        response = client.chat.completions.create(
            model=AZURE_CONFIG["deployment"],
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Reply briefly."},
                {"role": "user", "content": "What is 2 + 2? Reply with just the number."}
            ],
            max_completion_tokens=50,  # GPT-5.2 uses max_completion_tokens instead of max_tokens
        )

        answer = response.choices[0].message.content.strip()
        print(f"[OK] Chat completion successful")
        print(f"    Question: What is 2 + 2?")
        print(f"    Answer: {answer}")
        print(f"    Model: {response.model}")
        print(f"    Tokens: {response.usage.total_tokens}")

        return True

    except Exception as e:
        print(f"[ERROR] Chat completion failed: {e}")
        return False


def test_assistants_api(client):
    """Test 3: Assistants API (for Code Interpreter)"""
    print_section("Test 3: Assistants API")

    if not client:
        print("[SKIP] No client available")
        return False

    try:
        # List existing assistants
        assistants = client.beta.assistants.list(limit=5)
        print(f"[OK] Assistants API accessible")
        print(f"    Existing assistants: {len(assistants.data)}")

        for asst in assistants.data[:3]:
            tools = [t.type for t in asst.tools] if asst.tools else []
            print(f"    - {asst.name or asst.id}: tools={tools}")

        return True

    except Exception as e:
        print(f"[ERROR] Assistants API failed: {e}")
        print(f"    This may require Azure AI Foundry project setup")
        return False


def test_code_interpreter(client):
    """Test 4: Code Interpreter Functionality"""
    print_section("Test 4: Code Interpreter")

    if not client:
        print("[SKIP] No client available")
        return False

    assistant = None
    thread = None

    try:
        # Create assistant with code interpreter
        print("[INFO] Creating assistant with code_interpreter...")

        assistant = client.beta.assistants.create(
            name="Test Code Interpreter",
            instructions="You are a Python code execution assistant. Execute code and return results.",
            model=AZURE_CONFIG["deployment"],
            tools=[{"type": "code_interpreter"}],
        )
        print(f"[OK] Assistant created: {assistant.id}")

        # Create thread
        thread = client.beta.threads.create()
        print(f"[OK] Thread created: {thread.id}")

        # Add message with code execution request
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Calculate the factorial of 10 using Python. Show the code and result."
        )
        print(f"[OK] Message added: {message.id}")

        # Run the assistant
        print("[INFO] Running assistant (this may take a moment)...")
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            timeout=60,
        )

        print(f"[OK] Run completed: {run.status}")

        if run.status == "completed":
            # Get messages
            messages = client.beta.threads.messages.list(thread_id=thread.id)

            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "text":
                            print(f"\n[RESULT] Assistant response:")
                            print("-" * 40)
                            print(content.text.value[:500])
                            if len(content.text.value) > 500:
                                print("... (truncated)")
                            print("-" * 40)

            print("\n[OK] Code Interpreter test PASSED!")
            return True
        else:
            print(f"[ERROR] Run failed with status: {run.status}")
            if run.last_error:
                print(f"    Error: {run.last_error}")
            return False

    except Exception as e:
        print(f"[ERROR] Code Interpreter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if assistant:
            try:
                client.beta.assistants.delete(assistant.id)
                print(f"[CLEANUP] Deleted assistant: {assistant.id}")
            except:
                pass


def test_file_upload(client):
    """Test 5: File Upload for Code Interpreter"""
    print_section("Test 5: File Upload")

    if not client:
        print("[SKIP] No client available")
        return False

    try:
        import io

        # Create a simple CSV file in memory
        csv_content = b"name,value\nA,10\nB,20\nC,30\nD,40\nE,50"
        file_obj = io.BytesIO(csv_content)
        file_obj.name = "test_data.csv"

        # Upload file
        file = client.files.create(
            file=file_obj,
            purpose="assistants"
        )

        print(f"[OK] File uploaded successfully")
        print(f"    File ID: {file.id}")
        print(f"    Filename: {file.filename}")
        print(f"    Size: {file.bytes} bytes")
        print(f"    Purpose: {file.purpose}")

        # Cleanup
        client.files.delete(file.id)
        print(f"[CLEANUP] Deleted file: {file.id}")

        return True

    except Exception as e:
        print(f"[ERROR] File upload failed: {e}")
        return False


def test_visualization_code_interpreter(client):
    """Test 6: Visualization with Code Interpreter"""
    print_section("Test 6: Visualization Generation")

    if not client:
        print("[SKIP] No client available")
        return False

    assistant = None
    thread = None

    try:
        # Create assistant with code interpreter
        assistant = client.beta.assistants.create(
            name="Visualization Assistant",
            instructions="You are a data visualization assistant. Create charts using matplotlib.",
            model=AZURE_CONFIG["deployment"],
            tools=[{"type": "code_interpreter"}],
        )
        print(f"[OK] Visualization assistant created: {assistant.id}")

        # Create thread
        thread = client.beta.threads.create()

        # Request a chart
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="""Create a simple bar chart with this data:
            Categories: A, B, C, D
            Values: 25, 40, 30, 55

            Save the chart as 'chart.png' and show me the result."""
        )

        print("[INFO] Running visualization request...")
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            timeout=120,
        )

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)

            image_count = 0
            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "image_file":
                            image_count += 1
                            print(f"[OK] Image generated: {content.image_file.file_id}")
                        elif content.type == "text":
                            text = content.text.value[:200]
                            print(f"[INFO] Response: {text}...")

            if image_count > 0:
                print(f"\n[OK] Visualization test PASSED! Generated {image_count} image(s)")
                return True
            else:
                print("[WARN] No images generated, but run completed")
                return True
        else:
            print(f"[ERROR] Run failed: {run.status}")
            return False

    except Exception as e:
        print(f"[ERROR] Visualization test failed: {e}")
        return False

    finally:
        if assistant:
            try:
                client.beta.assistants.delete(assistant.id)
                print(f"[CLEANUP] Deleted assistant: {assistant.id}")
            except:
                pass


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  Azure AI Foundry Connection Test")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    results = {}

    # Test 1: Connection
    client = test_openai_connection()
    results["connection"] = client is not None

    # Test 2: Chat Completion
    results["chat"] = test_chat_completion(client)

    # Test 3: Assistants API
    results["assistants"] = test_assistants_api(client)

    # Test 4: Code Interpreter
    results["code_interpreter"] = test_code_interpreter(client)

    # Test 5: File Upload
    results["file_upload"] = test_file_upload(client)

    # Test 6: Visualization
    results["visualization"] = test_visualization_code_interpreter(client)

    # Summary
    print_section("Test Summary")

    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        icon = "[OK]" if passed else "[X]"
        print(f"  {icon} {test_name}: {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  All tests PASSED!")
        return 0
    else:
        print(f"\n  {total - passed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
