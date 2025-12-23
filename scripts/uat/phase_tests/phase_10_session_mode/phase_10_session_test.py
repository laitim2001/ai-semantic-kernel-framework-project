"""
Phase 10: Session Mode - Real Scenario Test
============================================

This test validates the Session Mode API by simulating a real multi-turn
conversation workflow with file analysis capabilities.

Test Scenario: Customer Support Session
- User creates a session to get help with a product
- User sends initial question
- System responds with clarifying questions
- User provides more details
- System provides comprehensive answer
- User ends the session

Endpoints Tested:
- POST /api/v1/sessions - Create session
- POST /api/v1/sessions/{id}/activate - Activate session
- POST /api/v1/sessions/{id}/messages - Send message
- GET /api/v1/sessions/{id}/messages - Get messages
- GET /api/v1/sessions/{id} - Get session details
- POST /api/v1/sessions/{id}/suspend - Suspend session
- POST /api/v1/sessions/{id}/resume - Resume session
"""

import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Test agent ID (valid UUID)
TEST_AGENT_ID = "00000000-0000-0000-0000-000000000002"


class SessionTestClient:
    """Session API Test Client"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.api_url = f"{base_url}{API_PREFIX}"

    def health_check(self) -> bool:
        """Check if the server is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def create_session(
        self,
        agent_id: str,
        title: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new session"""
        payload = {"agent_id": agent_id}
        if title:
            payload["title"] = title
        if config:
            payload["config"] = config

        response = requests.post(
            f"{self.api_url}/sessions",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details"""
        response = requests.get(f"{self.api_url}/sessions/{session_id}")
        response.raise_for_status()
        return response.json()

    def list_sessions(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List all sessions"""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status

        response = requests.get(f"{self.api_url}/sessions", params=params)
        response.raise_for_status()
        return response.json()

    def activate_session(self, session_id: str) -> Dict[str, Any]:
        """Activate a session"""
        response = requests.post(f"{self.api_url}/sessions/{session_id}/activate")
        response.raise_for_status()
        return response.json()

    def suspend_session(self, session_id: str) -> Dict[str, Any]:
        """Suspend a session"""
        response = requests.post(f"{self.api_url}/sessions/{session_id}/suspend")
        response.raise_for_status()
        return response.json()

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Resume a suspended session"""
        response = requests.post(f"{self.api_url}/sessions/{session_id}/resume")
        response.raise_for_status()
        return response.json()

    def send_message(
        self,
        session_id: str,
        content: str,
        role: str = "user",
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a session"""
        payload = {"content": content, "role": role}
        if attachments:
            payload["attachments"] = attachments

        response = requests.post(
            f"{self.api_url}/sessions/{session_id}/messages",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get messages from a session"""
        params = {"limit": limit}
        if before_id:
            params["before_id"] = before_id

        response = requests.get(
            f"{self.api_url}/sessions/{session_id}/messages", params=params
        )
        response.raise_for_status()
        return response.json()


def run_customer_support_scenario():
    """
    Run a real customer support scenario test.

    This simulates a multi-turn conversation where a user seeks help
    with a product issue.
    """
    print("=" * 60)
    print("Phase 10: Session Mode - Customer Support Scenario Test")
    print("=" * 60)
    print()

    client = SessionTestClient()
    results = {
        "timestamp": datetime.now().isoformat(),
        "scenario": "customer_support",
        "tests": [],
        "passed": 0,
        "failed": 0,
    }

    def record_test(name: str, success: bool, details: str = ""):
        status = "PASSED" if success else "FAILED"
        results["tests"].append({
            "name": name,
            "status": status,
            "details": details,
        })
        if success:
            results["passed"] += 1
        else:
            results["failed"] += 1
        print(f"  [{status}] {name}")
        if details:
            print(f"          {details}")

    # Test 1: Health Check
    print("\n1. Health Check")
    try:
        healthy = client.health_check()
        record_test("Server Health Check", healthy, "Server is responsive")
    except Exception as e:
        record_test("Server Health Check", False, str(e))
        print("\nERROR: Server is not running. Start the server first.")
        return results

    # Test 2: Create Session
    print("\n2. Create Customer Support Session")
    session_id = None
    try:
        session = client.create_session(
            agent_id=TEST_AGENT_ID,
            title="Customer Support - Product Issue",
            config={
                "max_messages": 50,
                "timeout_minutes": 30,
            },
        )
        session_id = session["id"]
        record_test(
            "Create Session",
            session_id is not None and session["status"] == "created",
            f"Session ID: {session_id}",
        )
    except Exception as e:
        record_test("Create Session", False, str(e))
        return results

    # Test 3: Activate Session
    print("\n3. Activate Session")
    try:
        activated = client.activate_session(session_id)
        record_test(
            "Activate Session",
            activated["status"] == "active",
            f"Status: {activated['status']}",
        )
    except Exception as e:
        record_test("Activate Session", False, str(e))
        return results

    # Test 4: First User Message
    print("\n4. Send First User Message (Initial Query)")
    try:
        message1 = client.send_message(
            session_id,
            content="Hi, I'm having trouble with my software subscription. "
            "It says my license has expired but I renewed it last week.",
            role="user",
        )
        record_test(
            "Send First Message",
            message1["id"] is not None and message1["role"] == "user",
            f"Message ID: {message1['id']}",
        )
    except Exception as e:
        record_test("Send First Message", False, str(e))

    # Test 5: Simulate Assistant Response
    # NOTE: API 設計上所有訊息都以 "user" 角色存儲 (安全考量)
    # 實際 assistant 訊息由 LLM 整合產生
    print("\n5. Simulate Assistant Response (stored as user)")
    try:
        response1 = client.send_message(
            session_id,
            content="I understand you're experiencing issues with your subscription. "
            "Let me help you resolve this. Could you please provide:\n"
            "1. Your account email\n"
            "2. The date you renewed\n"
            "3. Any confirmation number you received",
            role="assistant",  # Note: API ignores this, stores as "user"
        )
        record_test(
            "Send Assistant Response",
            response1["id"] is not None,  # API stores all as "user" (by design)
            f"Message ID: {response1['id']}",
        )
    except Exception as e:
        record_test("Send Assistant Response", False, str(e))

    # Test 6: User Provides Details
    print("\n6. User Provides Additional Details")
    try:
        message2 = client.send_message(
            session_id,
            content="My email is user@example.com. I renewed on December 20th, 2025. "
            "The confirmation number is REN-2025-12345.",
            role="user",
        )
        record_test(
            "Send User Details",
            message2["id"] is not None,
            f"Message ID: {message2['id']}",
        )
    except Exception as e:
        record_test("Send User Details", False, str(e))

    # Test 7: Get Message History
    print("\n7. Retrieve Conversation History")
    try:
        messages = client.get_messages(session_id)
        message_count = len(messages["data"])
        record_test(
            "Get Message History",
            message_count >= 3,
            f"Total messages: {message_count}",
        )
    except Exception as e:
        record_test("Get Message History", False, str(e))

    # Test 8: Get Session Details
    print("\n8. Get Session Details")
    try:
        session_details = client.get_session(session_id)
        record_test(
            "Get Session Details",
            session_details["status"] == "active",
            f"Status: {session_details['status']}, "
            f"Messages: {session_details.get('message_count', 'N/A')}",
        )
    except Exception as e:
        record_test("Get Session Details", False, str(e))

    # Test 9: Suspend Session
    print("\n9. Suspend Session (User Steps Away)")
    try:
        suspended = client.suspend_session(session_id)
        record_test(
            "Suspend Session",
            suspended["status"] == "suspended",
            f"Status: {suspended['status']}",
        )
    except Exception as e:
        record_test("Suspend Session", False, str(e))

    # Test 10: Resume Session
    print("\n10. Resume Session (User Returns)")
    try:
        resumed = client.resume_session(session_id)
        record_test(
            "Resume Session",
            resumed["status"] == "active",
            f"Status: {resumed['status']}",
        )
    except Exception as e:
        record_test("Resume Session", False, str(e))

    # Test 11: Continue Conversation
    print("\n11. Continue Conversation After Resume")
    try:
        message3 = client.send_message(
            session_id,
            content="Thank you for your patience. I found the issue - there was "
            "a sync delay. Your subscription is now active until December 20th, 2026.",
            role="assistant",
        )
        record_test(
            "Send Final Response",
            message3["id"] is not None,
            f"Message ID: {message3['id']}",
        )
    except Exception as e:
        record_test("Send Final Response", False, str(e))

    # Test 12: Final Message Count
    print("\n12. Verify Final Message Count")
    try:
        final_messages = client.get_messages(session_id)
        final_count = len(final_messages["data"])
        record_test(
            "Final Message Count",
            final_count >= 4,
            f"Total messages in session: {final_count}",
        )
    except Exception as e:
        record_test("Final Message Count", False, str(e))

    # Test 13: List Sessions
    print("\n13. List All Sessions")
    try:
        sessions = client.list_sessions()
        has_sessions = sessions["total"] > 0
        record_test(
            "List Sessions",
            has_sessions,
            f"Total sessions: {sessions['total']}",
        )
    except Exception as e:
        record_test("List Sessions", False, str(e))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['passed'] + results['failed']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    success_rate = (
        results["passed"] / (results["passed"] + results["failed"]) * 100
        if (results["passed"] + results["failed"]) > 0
        else 0
    )
    print(f"Success Rate: {success_rate:.1f}%")
    print()

    if results["failed"] == 0:
        print("ALL TESTS PASSED! Phase 10 Session Mode is fully functional.")
    else:
        print("Some tests failed. Please review the failures above.")

    return results


def save_results(results: Dict[str, Any], filename: str = None):
    """Save test results to a JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"phase_10_session_test_{timestamp}.json"

    filepath = f"scripts/uat/phase_tests/phase_10_session_mode/{filename}"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {filepath}")


if __name__ == "__main__":
    print()
    print("*" * 60)
    print("* Phase 10: Session Mode API - Real Scenario Test")
    print("* Testing multi-turn conversation capabilities")
    print("*" * 60)
    print()

    results = run_customer_support_scenario()
    save_results(results)
