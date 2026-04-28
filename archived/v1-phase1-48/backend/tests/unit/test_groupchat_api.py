# =============================================================================
# IPA Platform - GroupChat API Tests
# =============================================================================
# Sprint 9: S9-6 GroupChat API (8 points)
#
# Comprehensive tests for GroupChat API endpoints.
# =============================================================================

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.v1.groupchat.routes import router


# Create test app
app = FastAPI()
app.include_router(router)

client = TestClient(app)


# =============================================================================
# GroupChat API Tests
# =============================================================================


class TestGroupChatAPI:
    """Tests for GroupChat API endpoints."""

    def test_create_group_chat(self):
        """Test creating a group chat."""
        response = client.post("/groupchat/", json={
            "name": "Test Group",
            "description": "A test group chat",
            "agent_ids": ["agent-1", "agent-2", "agent-3"],
            "config": {
                "max_rounds": 10,
                "speaker_selection_method": "round_robin",
            },
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Group"
        assert data["status"] == "created"
        assert len(data["participants"]) == 3

    def test_list_group_chats(self):
        """Test listing group chats."""
        # Create some groups
        client.post("/groupchat/", json={
            "name": "Group 1",
            "agent_ids": ["agent-1"],
        })
        client.post("/groupchat/", json={
            "name": "Group 2",
            "agent_ids": ["agent-2"],
        })

        response = client.get("/groupchat/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_group_chat(self):
        """Test getting a specific group chat."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Get Test Group",
            "agent_ids": ["agent-1", "agent-2"],
        })
        group_id = create_response.json()["group_id"]

        # Get the group
        response = client.get(f"/groupchat/{group_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test Group"

    def test_get_nonexistent_group(self):
        """Test getting a non-existent group."""
        response = client.get(f"/groupchat/{uuid4()}")
        assert response.status_code == 404

    def test_update_group_config(self):
        """Test updating group configuration."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Config Test",
            "agent_ids": ["agent-1"],
        })
        group_id = create_response.json()["group_id"]

        # Update config
        response = client.patch(f"/groupchat/{group_id}/config", json={
            "max_rounds": 20,
            "allow_repeat_speaker": True,
        })

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_add_agent_to_group(self):
        """Test adding an agent to a group."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Add Agent Test",
            "agent_ids": ["agent-1"],
        })
        group_id = create_response.json()["group_id"]

        # Add agent
        response = client.post(
            f"/groupchat/{group_id}/agents/agent-new?name=NewAgent&capabilities=planning&capabilities=coding"
        )

        assert response.status_code == 200

    def test_remove_agent_from_group(self):
        """Test removing an agent from a group."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Remove Agent Test",
            "agent_ids": ["agent-1", "agent-2"],
        })
        group_id = create_response.json()["group_id"]

        # Remove agent
        response = client.delete(f"/groupchat/{group_id}/agents/agent-1")

        assert response.status_code == 200

    def test_send_message(self):
        """Test sending a message to group."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Message Test",
            "agent_ids": ["agent-1"],
        })
        group_id = create_response.json()["group_id"]

        # Send message
        response = client.post(f"/groupchat/{group_id}/message", json={
            "content": "Hello, group!",
            "sender_name": "user",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello, group!"
        assert data["sender_name"] == "user"

    def test_get_messages(self):
        """Test getting group messages."""
        # Create a group and send messages
        create_response = client.post("/groupchat/", json={
            "name": "Get Messages Test",
            "agent_ids": ["agent-1"],
        })
        group_id = create_response.json()["group_id"]

        client.post(f"/groupchat/{group_id}/message", json={
            "content": "Message 1",
            "sender_name": "user",
        })
        client.post(f"/groupchat/{group_id}/message", json={
            "content": "Message 2",
            "sender_name": "user",
        })

        # Get messages
        response = client.get(f"/groupchat/{group_id}/messages")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_transcript(self):
        """Test getting conversation transcript."""
        # Create a group and send messages
        create_response = client.post("/groupchat/", json={
            "name": "Transcript Test",
            "agent_ids": ["agent-1"],
        })
        group_id = create_response.json()["group_id"]

        client.post(f"/groupchat/{group_id}/message", json={
            "content": "Hello",
            "sender_name": "user",
        })

        # Get transcript
        response = client.get(f"/groupchat/{group_id}/transcript")

        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data

    def test_get_summary(self):
        """Test getting group summary."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Summary Test",
            "agent_ids": ["agent-1", "agent-2"],
        })
        group_id = create_response.json()["group_id"]

        # Get summary
        response = client.get(f"/groupchat/{group_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Summary Test"

    def test_terminate_group_chat(self):
        """Test terminating a group chat."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Terminate Test",
            "agent_ids": ["agent-1"],
        })
        group_id = create_response.json()["group_id"]

        # Terminate
        response = client.post(
            f"/groupchat/{group_id}/terminate?reason=test_termination"
        )

        assert response.status_code == 200

    def test_delete_group_chat(self):
        """Test deleting a group chat."""
        # Create a group
        create_response = client.post("/groupchat/", json={
            "name": "Delete Test",
            "agent_ids": ["agent-1"],
        })
        group_id = create_response.json()["group_id"]

        # Delete
        response = client.delete(f"/groupchat/{group_id}")

        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f"/groupchat/{group_id}")
        assert get_response.status_code == 404


# =============================================================================
# Multi-turn Session API Tests
# =============================================================================


class TestSessionAPI:
    """Tests for multi-turn session API endpoints."""

    def test_create_session(self):
        """Test creating a session."""
        response = client.post("/groupchat/sessions/", json={
            "user_id": "user-123",
            "initial_context": {"topic": "support"},
        })

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["status"] == "created"  # New session starts in 'created' status

    def test_list_sessions(self):
        """Test listing sessions."""
        # Create sessions
        client.post("/groupchat/sessions/", json={"user_id": "user-1"})
        client.post("/groupchat/sessions/", json={"user_id": "user-2"})

        response = client.get("/groupchat/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_list_sessions_by_user(self):
        """Test listing sessions by user."""
        # Create sessions
        client.post("/groupchat/sessions/", json={"user_id": "filter-user"})
        client.post("/groupchat/sessions/", json={"user_id": "filter-user"})
        client.post("/groupchat/sessions/", json={"user_id": "other-user"})

        response = client.get("/groupchat/sessions/?user_id=filter-user")

        assert response.status_code == 200
        data = response.json()
        assert all(s["user_id"] == "filter-user" for s in data)

    def test_get_session(self):
        """Test getting a session."""
        # Create session
        create_response = client.post("/groupchat/sessions/", json={
            "user_id": "get-user",
        })
        session_id = create_response.json()["session_id"]

        # Get session
        response = client.get(f"/groupchat/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "get-user"

    def test_get_nonexistent_session(self):
        """Test getting non-existent session."""
        response = client.get(f"/groupchat/sessions/{uuid4()}")
        assert response.status_code == 404

    def test_update_session_context(self):
        """Test updating session context."""
        # Create session
        create_response = client.post("/groupchat/sessions/", json={
            "user_id": "context-user",
            "initial_context": {"key1": "value1"},
        })
        session_id = create_response.json()["session_id"]

        # Update context
        response = client.patch(f"/groupchat/sessions/{session_id}/context", json={
            "context": {"key2": "value2"},
        })

        assert response.status_code == 200

    def test_close_session(self):
        """Test closing a session."""
        # Create session
        create_response = client.post("/groupchat/sessions/", json={
            "user_id": "close-user",
        })
        session_id = create_response.json()["session_id"]

        # Close
        response = client.post(f"/groupchat/sessions/{session_id}/close")

        assert response.status_code == 200

    def test_delete_session(self):
        """Test deleting a session."""
        # Create session
        create_response = client.post("/groupchat/sessions/", json={
            "user_id": "delete-user",
        })
        session_id = create_response.json()["session_id"]

        # Delete
        response = client.delete(f"/groupchat/sessions/{session_id}")

        assert response.status_code == 200


# =============================================================================
# Voting API Tests
# =============================================================================


class TestVotingAPI:
    """Tests for voting API endpoints."""

    def test_create_voting_session(self):
        """Test creating a voting session."""
        response = client.post("/groupchat/voting/", json={
            "topic": "Should we proceed?",
            "description": "Vote on the proposal",
            "vote_type": "approve_reject",
            "eligible_voters": ["voter-1", "voter-2", "voter-3"],
        })

        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Should we proceed?"
        assert data["vote_type"] == "approve_reject"

    def test_create_multiple_choice_voting(self):
        """Test creating multiple choice voting."""
        response = client.post("/groupchat/voting/", json={
            "topic": "Which option?",
            "vote_type": "multiple_choice",
            "options": ["A", "B", "C"],
        })

        assert response.status_code == 201
        data = response.json()
        assert data["options"] == ["A", "B", "C"]

    def test_list_voting_sessions(self):
        """Test listing voting sessions."""
        # Create sessions
        client.post("/groupchat/voting/", json={
            "topic": "Vote 1",
            "vote_type": "approve_reject",
        })
        client.post("/groupchat/voting/", json={
            "topic": "Vote 2",
            "vote_type": "approve_reject",
        })

        response = client.get("/groupchat/voting/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_voting_session(self):
        """Test getting a voting session."""
        # Create session
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Get Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        # Get session
        response = client.get(f"/groupchat/voting/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "Get Test"

    def test_cast_vote(self):
        """Test casting a vote."""
        # Create session
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Cast Vote Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        # Cast vote
        response = client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-1",
            "voter_name": "Alice",
            "choice": "approve",
            "reason": "I support this",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["choice"] == "approve"

    def test_cast_invalid_vote(self):
        """Test casting an invalid vote."""
        # Create session
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Invalid Vote Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        # Cast invalid vote
        response = client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-1",
            "voter_name": "Alice",
            "choice": "maybe",  # Invalid for approve_reject
        })

        assert response.status_code == 400

    def test_change_vote(self):
        """Test changing a vote."""
        # Create session and cast vote
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Change Vote Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-1",
            "voter_name": "Alice",
            "choice": "approve",
        })

        # Change vote
        response = client.patch(f"/groupchat/voting/{session_id}/vote/voter-1", json={
            "new_choice": "reject",
            "reason": "Changed my mind",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["choice"] == "reject"

    def test_withdraw_vote(self):
        """Test withdrawing a vote."""
        # Create session and cast vote
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Withdraw Vote Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-1",
            "voter_name": "Alice",
            "choice": "approve",
        })

        # Withdraw vote
        response = client.delete(f"/groupchat/voting/{session_id}/vote/voter-1")

        assert response.status_code == 200

    def test_get_votes(self):
        """Test getting all votes."""
        # Create session and cast votes
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Get Votes Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-1",
            "voter_name": "Alice",
            "choice": "approve",
        })
        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-2",
            "voter_name": "Bob",
            "choice": "reject",
        })

        # Get votes
        response = client.get(f"/groupchat/voting/{session_id}/votes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_calculate_result(self):
        """Test calculating voting result."""
        # Create session and cast votes
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Calculate Result Test",
            "vote_type": "approve_reject",
            "eligible_voters": ["voter-1", "voter-2", "voter-3"],
        })
        session_id = create_response.json()["session_id"]

        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-1",
            "voter_name": "Alice",
            "choice": "approve",
        })
        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-2",
            "voter_name": "Bob",
            "choice": "approve",
        })
        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-3",
            "voter_name": "Charlie",
            "choice": "reject",
        })

        # Calculate result
        response = client.post(f"/groupchat/voting/{session_id}/calculate")

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "passed"

    def test_get_voting_statistics(self):
        """Test getting voting statistics."""
        # Create session and cast vote
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Statistics Test",
            "vote_type": "approve_reject",
            "eligible_voters": ["voter-1", "voter-2"],
        })
        session_id = create_response.json()["session_id"]

        client.post(f"/groupchat/voting/{session_id}/vote", json={
            "voter_id": "voter-1",
            "voter_name": "Alice",
            "choice": "approve",
        })

        # Get statistics
        response = client.get(f"/groupchat/voting/{session_id}/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_votes"] == 1

    def test_close_voting_session(self):
        """Test closing a voting session."""
        # Create session
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Close Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        # Close
        response = client.post(f"/groupchat/voting/{session_id}/close")

        assert response.status_code == 200

    def test_cancel_voting_session(self):
        """Test cancelling a voting session."""
        # Create session
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Cancel Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        # Cancel
        response = client.post(
            f"/groupchat/voting/{session_id}/cancel?reason=test_cancellation"
        )

        assert response.status_code == 200

    def test_delete_voting_session(self):
        """Test deleting a voting session."""
        # Create session
        create_response = client.post("/groupchat/voting/", json={
            "topic": "Delete Test",
            "vote_type": "approve_reject",
        })
        session_id = create_response.json()["session_id"]

        # Delete
        response = client.delete(f"/groupchat/voting/{session_id}")

        assert response.status_code == 200

        # Verify deleted
        get_response = client.get(f"/groupchat/voting/{session_id}")
        assert get_response.status_code == 404


# =============================================================================
# Integration Tests
# =============================================================================


class TestAPIIntegration:
    """Integration tests for GroupChat API."""

    def test_complete_group_chat_flow(self):
        """Test complete group chat flow."""
        # Create group
        create_response = client.post("/groupchat/", json={
            "name": "Integration Test Group",
            "agent_ids": ["agent-1", "agent-2"],
        })
        assert create_response.status_code == 201
        group_id = create_response.json()["group_id"]

        # Send messages
        client.post(f"/groupchat/{group_id}/message", json={
            "content": "Hello everyone!",
            "sender_name": "user",
        })
        client.post(f"/groupchat/{group_id}/message", json={
            "content": "Hi there!",
            "sender_name": "agent-1",
        })

        # Get messages
        messages_response = client.get(f"/groupchat/{group_id}/messages")
        assert len(messages_response.json()) == 2

        # Get summary
        summary_response = client.get(f"/groupchat/{group_id}/summary")
        assert summary_response.json()["total_messages"] == 2

        # Terminate
        terminate_response = client.post(
            f"/groupchat/{group_id}/terminate?reason=completed"
        )
        assert terminate_response.status_code == 200

    def test_voting_in_group(self):
        """Test voting within a group chat."""
        # Create group
        create_group = client.post("/groupchat/", json={
            "name": "Voting Group",
            "agent_ids": ["agent-1", "agent-2", "agent-3"],
        })
        group_id = create_group.json()["group_id"]

        # Create voting session for the group
        create_voting = client.post("/groupchat/voting/", json={
            "group_id": group_id,
            "topic": "Should we use approach A?",
            "vote_type": "approve_reject",
            "eligible_voters": ["agent-1", "agent-2", "agent-3"],
        })
        session_id = create_voting.json()["session_id"]

        # Agents vote
        for i, choice in enumerate(["approve", "approve", "reject"]):
            client.post(f"/groupchat/voting/{session_id}/vote", json={
                "voter_id": f"agent-{i + 1}",
                "voter_name": f"Agent {i + 1}",
                "choice": choice,
            })

        # Calculate result
        result = client.post(f"/groupchat/voting/{session_id}/calculate")
        assert result.json()["result"] == "passed"
