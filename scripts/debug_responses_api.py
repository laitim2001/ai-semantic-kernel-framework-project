"""Debug script to trace Responses API error."""
import sys
import os
import traceback

# Environment variables should be set in .env file or system environment
# Required: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
# Example:
#   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
#   AZURE_OPENAI_API_KEY=your-api-key
#   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
#   AZURE_OPENAI_API_VERSION=2025-03-01-preview

sys.path.insert(0, "C:\\Users\\rci.ChrisLai\\Documents\\GitHub\\ai-semantic-kernel-framework-project\\backend")

# Configure logging to show debug messages
import logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

from src.integrations.agent_framework.builders.code_interpreter import (
    CodeInterpreterAdapter,
    CodeInterpreterConfig,
)

def test_execute():
    """Test execute with detailed tracing."""
    print("=" * 60)
    print("DEBUG: Testing Responses API Execute")
    print("=" * 60)

    try:
        config = CodeInterpreterConfig(timeout=60)
        adapter = CodeInterpreterAdapter(config=config)

        code = "print(1+1)"
        print(f"Executing code: {code}")

        result = adapter.execute(code=code)

        print(f"\nResult:")
        print(f"  success: {result.success}")
        print(f"  output: {result.output[:200] if result.output else 'empty'}")
        print(f"  error: {result.error}")
        print(f"  metadata: {result.metadata}")

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        print("\n--- Full Traceback ---")
        traceback.print_exc()

    finally:
        try:
            adapter.cleanup()
        except:
            pass


if __name__ == "__main__":
    test_execute()
