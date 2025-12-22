"""
Azure AI Agent Service Connection Test Script

This script verifies Azure AI Foundry Project connection and Code Interpreter functionality
using the OpenAI SDK (compatible with Azure AI Foundry)

Usage:
    python scripts/test_azure_ai_agent_service.py
"""

import os
import sys
import time
from pathlib import Path

# Configuration - Load from environment variables
PROJECT_ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
MODEL_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")


def check_dependencies():
    """Check required dependencies"""
    print("=" * 60)
    print("Step 1: Check Dependencies")
    print("=" * 60)

    missing = []

    try:
        import openai
        print(f"[OK] openai installed: {openai.__version__}")
    except ImportError:
        print("[FAIL] openai not installed")
        missing.append("openai")

    if missing:
        print(f"\n[WARNING] Please install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False

    return True


def test_chat_completion():
    """Test basic chat completion"""
    print("\n" + "=" * 60)
    print("Step 2: Test Chat Completion")
    print("=" * 60)

    from openai import AzureOpenAI

    print(f"[INFO] Endpoint: {AZURE_OPENAI_ENDPOINT}")
    print(f"[INFO] Model: {MODEL_DEPLOYMENT}")

    try:
        print("\n[PROGRESS] Creating AzureOpenAI client...")
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=API_KEY,
            api_version=API_VERSION,
        )
        print("[OK] Client created")

        print("\n[PROGRESS] Testing chat completion...")
        response = client.chat.completions.create(
            model=MODEL_DEPLOYMENT,
            messages=[
                {"role": "user", "content": "What is 2+2? Just give the number."}
            ],
            max_completion_tokens=50,
        )

        result = response.choices[0].message.content
        print(f"[OK] Chat completion successful!")
        print(f"[RESPONSE] {result}")

        return client

    except Exception as e:
        print(f"[FAIL] Chat completion failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_assistants_api(client):
    """Test Assistants API (Code Interpreter)"""
    print("\n" + "=" * 60)
    print("Step 3: Test Assistants API")
    print("=" * 60)

    try:
        print("[PROGRESS] Listing existing assistants...")
        assistants = client.beta.assistants.list()
        print(f"[OK] Found {len(assistants.data)} existing assistant(s)")

        for asst in assistants.data:
            print(f"    - {asst.name}: {asst.id}")

        return True

    except Exception as e:
        print(f"[WARNING] Assistants API not available: {e}")
        print("[INFO] This endpoint may not support Assistants API")
        return False


def test_code_interpreter(client):
    """Test Code Interpreter functionality"""
    print("\n" + "=" * 60)
    print("Step 4: Test Code Interpreter")
    print("=" * 60)

    try:
        print("[PROGRESS] Creating Assistant with Code Interpreter...")
        assistant = client.beta.assistants.create(
            name="IPA-CodeInterpreter-Test",
            instructions="You are a Python code execution assistant. Execute code and return results.",
            model=MODEL_DEPLOYMENT,
            tools=[{"type": "code_interpreter"}],
        )
        print(f"[OK] Assistant created: {assistant.id}")

        # Create a thread
        print("\n[PROGRESS] Creating conversation thread...")
        thread = client.beta.threads.create()
        print(f"[OK] Thread created: {thread.id}")

        # Add a message
        print("\n[PROGRESS] Sending code execution request...")
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Execute this Python code and tell me the result: print(sum(range(1, 101)))"
        )
        print(f"[OK] Message sent")

        # Run the assistant
        print("\n[PROGRESS] Running assistant (this may take a moment)...")
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        # Wait for completion
        max_wait = 60  # seconds
        start_time = time.time()
        while run.status in ["queued", "in_progress"]:
            if time.time() - start_time > max_wait:
                print(f"[TIMEOUT] Run took too long")
                break
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            print(f"    Status: {run.status}")

        print(f"[OK] Run completed with status: {run.status}")

        if run.status == "completed":
            # Get the response
            print("\n[PROGRESS] Getting response...")
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "text":
                            print(f"[RESPONSE] {content.text.value}")
                            break
                    break

            # Cleanup
            print("\n[PROGRESS] Cleaning up...")
            client.beta.assistants.delete(assistant.id)
            print("[OK] Assistant deleted")
            return True
        else:
            print(f"[WARNING] Run status: {run.status}")
            if hasattr(run, 'last_error') and run.last_error:
                print(f"   Error: {run.last_error}")
            # Cleanup
            client.beta.assistants.delete(assistant.id)
            return False

    except Exception as e:
        print(f"[FAIL] Code Interpreter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("   Azure AI Agent Service Connection Test")
    print("   IPA Platform - Code Interpreter Integration")
    print("=" * 60)

    results = {
        "dependencies": False,
        "chat_completion": False,
        "assistants_api": False,
        "code_interpreter": False
    }

    # Step 1: Check dependencies
    results["dependencies"] = check_dependencies()
    if not results["dependencies"]:
        print("\n[ABORT] Test aborted: Please install required packages")
        return

    # Step 2: Test chat completion
    client = test_chat_completion()
    if not client:
        print("\n[ABORT] Test aborted: Cannot establish connection")
        return
    results["chat_completion"] = True

    # Step 3: Test Assistants API availability
    results["assistants_api"] = test_assistants_api(client)

    # Step 4: Test Code Interpreter (if Assistants API is available)
    if results["assistants_api"]:
        results["code_interpreter"] = test_code_interpreter(client)
    else:
        print("\n[SKIP] Code Interpreter test skipped (Assistants API not available)")

    # Summary
    print("\n" + "=" * 60)
    print("   Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        if test_name == "code_interpreter" and not results["assistants_api"]:
            status = "[SKIP]"
        else:
            status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test_name.replace('_', ' ').title()}")

    # Check if basic functionality works
    if results["chat_completion"]:
        print("\n[SUCCESS] Azure OpenAI connection is working!")
        if results["code_interpreter"]:
            print("[SUCCESS] Code Interpreter is available!")
        elif results["assistants_api"]:
            print("[INFO] Assistants API available but Code Interpreter test failed")
        else:
            print("[INFO] Assistants API not available on this endpoint")
            print("[HINT] Code Interpreter requires Azure AI Agent Service (AI Foundry)")
    else:
        print("\n[FAIL] Cannot connect to Azure OpenAI")


if __name__ == "__main__":
    main()
