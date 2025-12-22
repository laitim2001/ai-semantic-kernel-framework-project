"""
Test OpenAI Responses API (New API replacing Assistants API)

This script demonstrates:
1. Responses API with code_interpreter tool
2. File upload and processing
3. Downloading generated files (charts, etc.) to local disk

Reference: https://platform.openai.com/docs/api-reference/responses
"""

import os
import sys
import io
import base64
from datetime import datetime
from pathlib import Path

# Azure AI Foundry Configuration - Load from environment variables
AZURE_CONFIG = {
    "api_version": os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
    "subscription_key": os.environ.get("AZURE_OPENAI_API_KEY", ""),
}

# Output directory for downloaded files
OUTPUT_DIR = Path(__file__).parent / "output"


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def get_client():
    """Create Azure OpenAI client."""
    from openai import AzureOpenAI

    return AzureOpenAI(
        api_version=AZURE_CONFIG["api_version"],
        azure_endpoint=AZURE_CONFIG["azure_endpoint"],
        api_key=AZURE_CONFIG["subscription_key"],
    )


def test_responses_api_basic(client):
    """Test 1: Basic Responses API (if available)."""
    print_section("Test 1: Responses API (New API)")

    try:
        # Check if Responses API is available
        if hasattr(client, 'responses'):
            print("[INFO] Responses API detected in client")

            response = client.responses.create(
                model=AZURE_CONFIG["deployment"],
                input="Calculate 15 * 23 using Python code",
                tools=[{"type": "code_interpreter"}],
            )

            print(f"[OK] Responses API call successful")
            print(f"    Response ID: {response.id}")
            print(f"    Output: {response.output}")
            return True
        else:
            print("[INFO] Responses API not available in current SDK version")
            print("       Using Assistants API as fallback (still functional)")
            return None

    except AttributeError as e:
        print(f"[INFO] Responses API not available: {e}")
        print("       This is expected - Responses API is still in preview")
        return None
    except Exception as e:
        print(f"[ERROR] Responses API test failed: {e}")
        return False


def test_file_creation_local(client):
    """Test 2: Show where files are created."""
    print_section("Test 2: File Creation Locations")

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"[INFO] Output directory: {OUTPUT_DIR.absolute()}")

    # Method 1: In-memory file (BytesIO)
    print("\n--- Method 1: In-Memory File (BytesIO) ---")
    csv_content = b"name,value\nApple,100\nBanana,200\nCherry,150\nDate,300\nEldberry,250"
    file_obj = io.BytesIO(csv_content)
    file_obj.name = "sales_data.csv"

    print(f"[OK] Created in-memory file: {file_obj.name}")
    print(f"    Content: {csv_content.decode()[:50]}...")
    print(f"    Size: {len(csv_content)} bytes")
    print(f"    Location: RAM (io.BytesIO object)")

    # Method 2: Local file saved to disk
    print("\n--- Method 2: Local File (Saved to Disk) ---")
    local_csv_path = OUTPUT_DIR / "local_sales_data.csv"
    with open(local_csv_path, 'wb') as f:
        f.write(csv_content)

    print(f"[OK] Created local file: {local_csv_path}")
    print(f"    Location: {local_csv_path.absolute()}")

    # Upload to Azure
    print("\n--- Upload to Azure ---")
    try:
        file = client.files.create(
            file=file_obj,
            purpose="assistants"
        )
        print(f"[OK] Uploaded to Azure")
        print(f"    Azure File ID: {file.id}")
        print(f"    Filename: {file.filename}")
        print(f"    Purpose: {file.purpose}")

        # Cleanup
        client.files.delete(file.id)
        print(f"[CLEANUP] Deleted from Azure: {file.id}")

        return True

    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return False


def test_download_generated_chart(client):
    """Test 3: Generate chart and download to local disk."""
    print_section("Test 3: Generate & Download Chart")

    OUTPUT_DIR.mkdir(exist_ok=True)
    assistant = None
    thread = None
    downloaded_files = []

    try:
        # Create assistant with code interpreter
        print("[INFO] Creating assistant with code_interpreter...")
        assistant = client.beta.assistants.create(
            name="Chart Generator",
            instructions="You are a data visualization expert. Create beautiful charts using matplotlib and save them as PNG files.",
            model=AZURE_CONFIG["deployment"],
            tools=[{"type": "code_interpreter"}],
        )
        print(f"[OK] Assistant created: {assistant.id}")

        # Create thread
        thread = client.beta.threads.create()
        print(f"[OK] Thread created: {thread.id}")

        # Request a chart with specific data
        chart_request = """
Please create a professional bar chart with the following sales data:

| Product    | Q1 Sales | Q2 Sales |
|------------|----------|----------|
| Laptops    | 150      | 180      |
| Phones     | 200      | 220      |
| Tablets    | 80       | 95       |
| Watches    | 120      | 150      |
| Headphones | 90       | 110      |

Requirements:
1. Use a grouped bar chart (Q1 and Q2 side by side)
2. Add a title: "Product Sales Comparison Q1 vs Q2"
3. Add axis labels
4. Use a professional color scheme
5. Save as 'sales_chart.png' with dpi=150

Please generate and save the chart.
"""

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=chart_request
        )
        print(f"[OK] Message added: {message.id}")

        # Run the assistant
        print("[INFO] Running assistant (generating chart)...")
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            timeout=120,
        )

        print(f"[OK] Run completed: {run.status}")

        if run.status == "completed":
            # Get messages and find generated files
            messages = client.beta.threads.messages.list(thread_id=thread.id)

            print("\n--- Searching for generated files ---")

            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "image_file":
                            file_id = content.image_file.file_id
                            print(f"\n[FOUND] Image file: {file_id}")

                            # Download the file content
                            print("[INFO] Downloading file content...")
                            file_content = client.files.content(file_id)

                            # Save to local disk
                            local_path = OUTPUT_DIR / f"downloaded_chart_{len(downloaded_files) + 1}.png"
                            with open(local_path, 'wb') as f:
                                f.write(file_content.read())

                            downloaded_files.append(local_path)
                            print(f"[OK] Saved to: {local_path.absolute()}")
                            print(f"    File size: {local_path.stat().st_size} bytes")

                        elif content.type == "text":
                            # Show part of the response
                            text = content.text.value
                            if "chart" in text.lower() or "save" in text.lower():
                                print(f"\n[INFO] Assistant response (excerpt):")
                                print("-" * 40)
                                print(text[:300])
                                if len(text) > 300:
                                    print("...")
                                print("-" * 40)

            # Summary
            print(f"\n--- Download Summary ---")
            print(f"Total files downloaded: {len(downloaded_files)}")
            for path in downloaded_files:
                print(f"  - {path.absolute()}")

            if downloaded_files:
                print(f"\n[OK] Chart download test PASSED!")
                return True
            else:
                print(f"[WARN] No image files found in response")
                return False

        else:
            print(f"[ERROR] Run failed: {run.status}")
            if run.last_error:
                print(f"    Error: {run.last_error}")
            return False

    except Exception as e:
        print(f"[ERROR] Chart generation/download failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup assistant
        if assistant:
            try:
                client.beta.assistants.delete(assistant.id)
                print(f"\n[CLEANUP] Deleted assistant: {assistant.id}")
            except:
                pass


def test_upload_and_analyze_csv(client):
    """Test 4: Upload CSV and have Code Interpreter analyze it."""
    print_section("Test 4: Upload CSV & Analyze with Code Interpreter")

    OUTPUT_DIR.mkdir(exist_ok=True)
    assistant = None
    thread = None
    uploaded_file = None

    try:
        # Create a more complex CSV file
        csv_content = """date,product,region,sales,units
2024-01-01,Laptop,North,15000,10
2024-01-01,Laptop,South,12000,8
2024-01-01,Phone,North,8000,20
2024-01-01,Phone,South,9500,25
2024-01-02,Laptop,North,14500,9
2024-01-02,Laptop,South,13000,9
2024-01-02,Phone,North,8500,22
2024-01-02,Phone,South,10000,28
2024-01-03,Laptop,North,16000,11
2024-01-03,Laptop,South,11500,7
2024-01-03,Phone,North,7500,18
2024-01-03,Phone,South,11000,30"""

        # Save locally first
        local_csv = OUTPUT_DIR / "analysis_data.csv"
        with open(local_csv, 'w') as f:
            f.write(csv_content)
        print(f"[OK] Created local CSV: {local_csv}")

        # Upload to Azure
        with open(local_csv, 'rb') as f:
            uploaded_file = client.files.create(
                file=f,
                purpose="assistants"
            )
        print(f"[OK] Uploaded to Azure: {uploaded_file.id}")

        # Create assistant
        assistant = client.beta.assistants.create(
            name="Data Analyst",
            instructions="You are a data analyst. Analyze data files and create visualizations. Always save charts as PNG files.",
            model=AZURE_CONFIG["deployment"],
            tools=[{"type": "code_interpreter"}],
        )
        print(f"[OK] Assistant created: {assistant.id}")

        # Create thread with file attachment
        thread = client.beta.threads.create()

        # Add message with file
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="""Please analyze the attached CSV file and:
1. Show a summary of total sales by product
2. Create a pie chart showing sales distribution by region
3. Save the chart as 'region_sales.png'
""",
            attachments=[{
                "file_id": uploaded_file.id,
                "tools": [{"type": "code_interpreter"}]
            }]
        )
        print(f"[OK] Message with attachment added")

        # Run
        print("[INFO] Running analysis...")
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            timeout=120,
        )

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)

            print("\n--- Analysis Results ---")
            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "image_file":
                            file_id = content.image_file.file_id
                            file_content = client.files.content(file_id)

                            local_path = OUTPUT_DIR / "analysis_chart.png"
                            with open(local_path, 'wb') as f:
                                f.write(file_content.read())

                            print(f"[OK] Chart saved: {local_path}")

                        elif content.type == "text":
                            print(content.text.value[:500])

            print(f"\n[OK] CSV analysis test PASSED!")
            return True

        else:
            print(f"[ERROR] Run failed: {run.status}")
            return False

    except Exception as e:
        print(f"[ERROR] CSV analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if uploaded_file:
            try:
                client.files.delete(uploaded_file.id)
                print(f"[CLEANUP] Deleted uploaded file: {uploaded_file.id}")
            except:
                pass
        if assistant:
            try:
                client.beta.assistants.delete(assistant.id)
                print(f"[CLEANUP] Deleted assistant: {assistant.id}")
            except:
                pass


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  OpenAI Responses API & File Download Test")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    # Suppress deprecation warnings
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    client = get_client()
    print(f"[OK] Client created")

    results = {}

    # Test 1: Responses API
    result = test_responses_api_basic(client)
    results["responses_api"] = result if result is not None else "N/A (using Assistants API)"

    # Test 2: File creation locations
    results["file_creation"] = test_file_creation_local(client)

    # Test 3: Download generated chart
    results["download_chart"] = test_download_generated_chart(client)

    # Test 4: Upload and analyze CSV
    results["csv_analysis"] = test_upload_and_analyze_csv(client)

    # Summary
    print_section("Test Summary")

    for test_name, passed in results.items():
        if passed == "N/A (using Assistants API)":
            print(f"  [~] {test_name}: {passed}")
        elif passed:
            print(f"  [OK] {test_name}: PASSED")
        else:
            print(f"  [X] {test_name}: FAILED")

    print(f"\n  Output directory: {OUTPUT_DIR.absolute()}")

    # List downloaded files
    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.glob("*"))
        if files:
            print(f"\n  Downloaded files:")
            for f in files:
                print(f"    - {f.name} ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
