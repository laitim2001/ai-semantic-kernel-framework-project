#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Azure OpenAI Connection Test
============================
驗證 Azure OpenAI 連接是否正常
"""

import io
import os
import sys

# Windows 編碼修復
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv

# 載入 .env 文件
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

print("=" * 60)
print("Azure OpenAI Connection Test")
print("=" * 60)

# 檢查環境變數
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

print(f"\n📋 Configuration:")
print(f"   Endpoint: {endpoint}")
print(f"   Deployment: {deployment}")
print(f"   API Version: {api_version}")
print(f"   API Key: {api_key[:20]}..." if api_key else "   API Key: Not set")

if not all([endpoint, api_key, deployment]):
    print("\n❌ Missing required environment variables!")
    sys.exit(1)

print("\n🔄 Testing connection...")

try:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    # 簡單測試
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, Azure OpenAI is working!' in Chinese."}
        ],
        max_completion_tokens=50,
        temperature=0.7,
    )

    result = response.choices[0].message.content
    print(f"\n✅ Connection successful!")
    print(f"\n📝 Response: {result}")

    # 顯示 token 使用
    usage = response.usage
    print(f"\n📊 Token Usage:")
    print(f"   Prompt tokens: {usage.prompt_tokens}")
    print(f"   Completion tokens: {usage.completion_tokens}")
    print(f"   Total tokens: {usage.total_tokens}")

    print("\n" + "=" * 60)
    print("✅ Azure OpenAI connection test PASSED!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ Connection failed: {e}")
    print("\n" + "=" * 60)
    print("❌ Azure OpenAI connection test FAILED!")
    print("=" * 60)
    sys.exit(1)
