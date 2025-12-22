"""
Direct Azure OpenAI Connection Test

Tests the Azure OpenAI deployment directly (without AI Foundry)
to verify the deployment exists and works.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load .env from backend
env_path = Path(__file__).parent.parent / "backend" / ".env"
load_dotenv(env_path)

# Get configuration from environment
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.2")
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")


def test_direct_connection():
    """Test Azure OpenAI deployment directly"""
    print("=" * 60)
    print("Direct Azure OpenAI Connection Test")
    print("=" * 60)
    print(f"Endpoint: {AZURE_OPENAI_ENDPOINT}")
    print(f"Deployment: {DEPLOYMENT_NAME}")
    print(f"API Version: {API_VERSION}")
    print()

    # Check for API key
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] AZURE_OPENAI_API_KEY environment variable not set")
        print("[HINT] Set it with: set AZURE_OPENAI_API_KEY=your-key-here")
        return False

    try:
        print("[PROGRESS] Creating AzureOpenAI client...")
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=api_key,
            api_version=API_VERSION,
        )
        print("[OK] Client created")

        print("[PROGRESS] Testing chat completion...")
        # Try with max_completion_tokens first (newer models), fallback to max_tokens
        try:
            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=[
                    {"role": "user", "content": "Say 'Hello' in one word."}
                ],
                max_completion_tokens=10
            )
        except Exception:
            response = client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=[
                    {"role": "user", "content": "Say 'Hello' in one word."}
                ],
                max_tokens=10
            )

        result = response.choices[0].message.content
        print(f"[OK] Response received: {result}")
        print()
        print("[SUCCESS] Azure OpenAI deployment is working!")
        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


if __name__ == "__main__":
    test_direct_connection()
