# -*- coding: utf-8 -*-
"""Wrapper to run enterprise_outage_test.py with .env loaded"""
import sys
import os
import asyncio

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Load .env file BEFORE importing the test
from dotenv import load_dotenv
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

print(f"[INFO] Loaded environment from: {env_path}")
print(f"[INFO] AZURE_OPENAI_ENDPOINT: {'Set' if os.getenv('AZURE_OPENAI_ENDPOINT') else 'Not set'}")
print(f"[INFO] AZURE_OPENAI_API_KEY: {'Set' if os.getenv('AZURE_OPENAI_API_KEY') else 'Not set'}")
print()

# Import and run the test
from enterprise_outage_test import main

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
