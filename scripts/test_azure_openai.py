"""
Test Azure OpenAI Connection
驗證 Azure OpenAI API 連接是否正常工作
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load .env from backend
load_dotenv(backend_path / ".env")


async def test_azure_openai_connection():
    """Test Azure OpenAI connection with a simple completion request."""
    from openai import AzureOpenAI

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    print("=" * 60)
    print(" Azure OpenAI Connection Test")
    print("=" * 60)
    print(f"\nEndpoint: {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"API Version: {api_version}")
    print(f"API Key: {'*' * 8}...{api_key[-8:] if api_key else 'NOT SET'}")
    print()

    if not all([endpoint, api_key, deployment]):
        print("[ERROR] Missing Azure OpenAI configuration!")
        return False

    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

        print("[INFO] Sending test request to Azure OpenAI...")
        print("-" * 60)

        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Respond briefly in Traditional Chinese."},
                {"role": "user", "content": "Hello! Please confirm you are working by saying 'Azure OpenAI connection successful' in Traditional Chinese."}
            ],
            max_completion_tokens=100,
            temperature=0.7
        )

        assistant_message = response.choices[0].message.content

        print(f"\n[SUCCESS] Response from Azure OpenAI:")
        print(f"  Model: {response.model}")
        # Handle encoding for Windows console
        try:
            print(f"  Message: {assistant_message}")
        except UnicodeEncodeError:
            print(f"  Message: {assistant_message.encode('ascii', 'replace').decode('ascii')}")
        print(f"  Tokens used: {response.usage.total_tokens}")
        print("-" * 60)
        print("\n[PASS] Azure OpenAI connection is working!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to connect to Azure OpenAI: {e}")
        return False


def test_config_loading():
    """Test if config loads Azure OpenAI settings correctly."""
    print("\n" + "=" * 60)
    print(" Configuration Loading Test")
    print("=" * 60)

    try:
        # Change to backend directory for proper .env loading
        original_cwd = os.getcwd()
        os.chdir(backend_path)

        from src.core.config import get_settings

        # Clear cache to reload settings
        get_settings.cache_clear()
        settings = get_settings()

        os.chdir(original_cwd)

        print(f"\nAzure OpenAI Endpoint: {settings.azure_openai_endpoint}")
        print(f"Azure OpenAI Deployment: {settings.azure_openai_deployment_name}")
        print(f"Azure OpenAI API Version: {settings.azure_openai_api_version}")
        print(f"Is Configured: {settings.is_azure_openai_configured}")

        if settings.is_azure_openai_configured:
            print("\n[PASS] Configuration loaded successfully!")
            return True
        else:
            print("\n[WARN] Azure OpenAI not configured in settings")
            return False

    except Exception as e:
        print(f"\n[ERROR] Failed to load config: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" IPA Platform - Azure OpenAI Integration Test")
    print("=" * 60)

    # Test 1: Config loading
    config_ok = test_config_loading()

    # Test 2: Azure OpenAI connection
    connection_ok = asyncio.run(test_azure_openai_connection())

    print("\n" + "=" * 60)
    print(" Test Summary")
    print("=" * 60)
    print(f"  Configuration Loading: {'PASS' if config_ok else 'FAIL'}")
    print(f"  Azure OpenAI Connection: {'PASS' if connection_ok else 'FAIL'}")
    print("=" * 60)

    sys.exit(0 if (config_ok and connection_ok) else 1)
