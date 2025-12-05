# =============================================================================
# IPA Platform - Voting Manager Tests
# =============================================================================
# Sprint 9: S9-5 VotingManager (5 points)
#
# Comprehensive tests for voting management.
# =============================================================================

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.orchestration.groupchat.voting import (
    Vote,
    VoteResult,
    VoteType,
    VotingManager,
    VotingSession,
    VotingSessionStatus,
)


# =============================================================================
# Vote Tests
# =============================================================================


class TestVote:
    """Tests for Vote dataclass."""

    def test_create_vote(self):
        """Test creating a vote."""
        vote = Vote(
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
            weight=1.5,
        )

        assert vote.voter_id == "agent-1"
        assert vote.voter_name == "Alice"
        assert vote.choice == "approve"
        assert vote.weight == 1.5
        assert vote.vote_id is not None

    def test_vote_to_dict(self):
        """Test converting vote to dictionary."""
        vote = Vote(
            voter_id="agent-1",
            choice="approve",
            reason="I support this",
        )

        data = vote.to_dict()

        assert data["voter_id"] == "agent-1"
        assert data["choice"] == "approve"
        assert data["reason"] == "I support this"

    def test_vote_with_metadata(self):
        """Test vote with metadata."""
        vote = Vote(
            voter_id="agent-1",
            choice="approve",
            metadata={"confidence": 0.95},
        )

        assert vote.metadata["confidence"] == 0.95


# =============================================================================
# VotingSession Tests
# =============================================================================


class TestVotingSession:
    """Tests for VotingSession dataclass."""

    def test_create_session(self):
        """Test creating a voting session."""
        session = VotingSession(
            topic="Should we proceed?",
            vote_type=VoteType.APPROVE_REJECT,
            options=["approve", "reject"],
        )

        assert session.topic == "Should we proceed?"
        assert session.vote_type == VoteType.APPROVE_REJECT
        assert session.status == VotingSessionStatus.OPEN

    def test_session_properties(self):
        """Test session properties."""
        session = VotingSession(
            eligible_voters={"agent-1", "agent-2", "agent-3"},
        )

        assert session.vote_count == 0
        assert session.participation_rate == 0.0
        assert session.is_open is True
        assert session.is_expired is False

    def test_session_expiration(self):
        """Test session expiration."""
        # Not expired
        session = VotingSession(
            deadline=datetime.utcnow() + timedelta(hours=1),
        )
        assert session.is_expired is False
        assert session.is_open is True

        # Expired
        expired_session = VotingSession(
            deadline=datetime.utcnow() - timedelta(hours=1),
        )
        assert expired_session.is_expired is True
        assert expired_session.is_open is False

    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        session = VotingSession(
            topic="Test topic",
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=["A", "B", "C"],
        )

        data = session.to_dict()

        assert data["topic"] == "Test topic"
        assert data["vote_type"] == "multiple_choice"
        assert data["options"] == ["A", "B", "C"]


# =============================================================================
# VotingManager Tests
# =============================================================================


class TestVotingManager:
    """Tests for VotingManager."""

    @pytest.fixture
    def manager(self):
        """Create a VotingManager for each test."""
        return VotingManager()

    # -------------------------------------------------------------------------
    # Session Management Tests
    # -------------------------------------------------------------------------

    def test_create_session(self, manager):
        """Test creating a voting session."""
        session = manager.create_session(
            topic="Should we approve this change?",
            vote_type=VoteType.APPROVE_REJECT,
        )

        assert session.topic == "Should we approve this change?"
        assert session.vote_type == VoteType.APPROVE_REJECT
        assert session.options == ["approve", "reject"]

    def test_create_multiple_choice_session(self, manager):
        """Test creating a multiple choice session."""
        session = manager.create_session(
            topic="Which option do you prefer?",
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=["Option A", "Option B", "Option C"],
        )

        assert session.vote_type == VoteType.MULTIPLE_CHOICE
        assert len(session.options) == 3

    def test_create_ranking_session(self, manager):
        """Test creating a ranking session."""
        session = manager.create_session(
            topic="Rank these options",
            vote_type=VoteType.RANKING,
            options=["First", "Second", "Third"],
        )

        assert session.vote_type == VoteType.RANKING
        assert len(session.options) == 3

    def test_create_session_with_deadline(self, manager):
        """Test creating session with deadline."""
        session = manager.create_session(
            topic="Quick vote",
            deadline_minutes=30,
        )

        assert session.deadline is not None
        assert session.deadline > datetime.utcnow()

    def test_create_session_with_quorum(self, manager):
        """Test creating session with custom quorum."""
        session = manager.create_session(
            topic="Important decision",
            required_quorum=0.75,
            pass_threshold=0.6,
        )

        assert session.required_quorum == 0.75
        assert session.pass_threshold == 0.6

    def test_create_session_with_eligible_voters(self, manager):
        """Test creating session with eligible voters."""
        voters = {"agent-1", "agent-2", "agent-3"}
        session = manager.create_session(
            topic="Test",
            eligible_voters=voters,
        )

        assert session.eligible_voters == voters

    def test_create_multiple_choice_without_options_raises(self, manager):
        """Test that creating multiple choice without options raises error."""
        with pytest.raises(ValueError):
            manager.create_session(
                topic="Test",
                vote_type=VoteType.MULTIPLE_CHOICE,
                options=None,
            )

    def test_get_session(self, manager):
        """Test getting a session by ID."""
        session = manager.create_session(topic="Test")

        retrieved = manager.get_session(session.session_id)
        assert retrieved == session

    def test_get_nonexistent_session(self, manager):
        """Test getting non-existent session."""
        session = manager.get_session(uuid4())
        assert session is None

    def test_list_sessions(self, manager):
        """Test listing sessions."""
        group_id = uuid4()

        manager.create_session(topic="Test 1", group_id=group_id)
        manager.create_session(topic="Test 2", group_id=group_id)
        manager.create_session(topic="Test 3")  # Different group

        all_sessions = manager.list_sessions()
        assert len(all_sessions) == 3

        group_sessions = manager.list_sessions(group_id=group_id)
        assert len(group_sessions) == 2

    def test_list_sessions_by_status(self, manager):
        """Test listing sessions by status."""
        s1 = manager.create_session(topic="Test 1")
        s2 = manager.create_session(topic="Test 2")
        manager.close_session(s1.session_id)

        open_sessions = manager.list_sessions(status=VotingSessionStatus.OPEN)
        assert len(open_sessions) == 1

        closed_sessions = manager.list_sessions(status=VotingSessionStatus.CLOSED)
        assert len(closed_sessions) == 1

    def test_close_session(self, manager):
        """Test closing a session."""
        session = manager.create_session(topic="Test")

        result = manager.close_session(session.session_id)
        assert result is True

        updated = manager.get_session(session.session_id)
        assert updated.status == VotingSessionStatus.CLOSED

    def test_cancel_session(self, manager):
        """Test cancelling a session."""
        session = manager.create_session(topic="Test")

        result = manager.cancel_session(session.session_id, "Changed plans")
        assert result is True

        updated = manager.get_session(session.session_id)
        assert updated.status == VotingSessionStatus.CANCELLED
        assert updated.result == VoteResult.CANCELLED

    def test_delete_session(self, manager):
        """Test deleting a session."""
        session = manager.create_session(topic="Test")

        result = manager.delete_session(session.session_id)
        assert result is True

        retrieved = manager.get_session(session.session_id)
        assert retrieved is None

    # -------------------------------------------------------------------------
    # Voting Tests
    # -------------------------------------------------------------------------

    def test_cast_vote(self, manager):
        """Test casting a vote."""
        session = manager.create_session(topic="Test")

        vote = manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
        )

        assert vote.voter_id == "agent-1"
        assert vote.choice == "approve"
        assert session.vote_count == 1

    def test_cast_vote_with_weight(self, manager):
        """Test casting a weighted vote."""
        session = manager.create_session(topic="Test")

        vote = manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
            weight=2.0,
        )

        assert vote.weight == 2.0

    def test_cast_vote_with_reason(self, manager):
        """Test casting a vote with reason."""
        session = manager.create_session(topic="Test")

        vote = manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
            reason="I agree with this proposal",
        )

        assert vote.reason == "I agree with this proposal"

    def test_cast_vote_invalid_choice(self, manager):
        """Test casting vote with invalid choice."""
        session = manager.create_session(
            topic="Test",
            vote_type=VoteType.APPROVE_REJECT,
        )

        with pytest.raises(ValueError, match="must be 'approve' or 'reject'"):
            manager.cast_vote(
                session.session_id,
                voter_id="agent-1",
                voter_name="Alice",
                choice="maybe",
            )

    def test_cast_vote_ineligible_voter(self, manager):
        """Test casting vote by ineligible voter."""
        session = manager.create_session(
            topic="Test",
            eligible_voters={"agent-1", "agent-2"},
        )

        with pytest.raises(ValueError, match="not eligible"):
            manager.cast_vote(
                session.session_id,
                voter_id="agent-3",  # Not in eligible list
                voter_name="Charlie",
                choice="approve",
            )

    def test_cast_vote_closed_session(self, manager):
        """Test casting vote on closed session."""
        session = manager.create_session(topic="Test")
        manager.close_session(session.session_id)

        with pytest.raises(ValueError, match="not open"):
            manager.cast_vote(
                session.session_id,
                voter_id="agent-1",
                voter_name="Alice",
                choice="approve",
            )

    def test_cast_vote_nonexistent_session(self, manager):
        """Test casting vote on non-existent session."""
        with pytest.raises(ValueError, match="not found"):
            manager.cast_vote(
                uuid4(),
                voter_id="agent-1",
                voter_name="Alice",
                choice="approve",
            )

    def test_cast_multiple_choice_vote(self, manager):
        """Test casting multiple choice vote."""
        session = manager.create_session(
            topic="Choose one",
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=["A", "B", "C"],
        )

        vote = manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="B",
        )

        assert vote.choice == "B"

    def test_cast_multiple_choice_invalid(self, manager):
        """Test casting invalid multiple choice vote."""
        session = manager.create_session(
            topic="Choose one",
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=["A", "B", "C"],
        )

        with pytest.raises(ValueError, match="Invalid choice"):
            manager.cast_vote(
                session.session_id,
                voter_id="agent-1",
                voter_name="Alice",
                choice="D",  # Not in options
            )

    def test_cast_ranking_vote(self, manager):
        """Test casting ranking vote."""
        session = manager.create_session(
            topic="Rank these",
            vote_type=VoteType.RANKING,
            options=["X", "Y", "Z"],
        )

        vote = manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice=["Z", "X", "Y"],  # Ranking
        )

        assert vote.choice == ["Z", "X", "Y"]

    def test_cast_ranking_incomplete(self, manager):
        """Test casting incomplete ranking vote."""
        session = manager.create_session(
            topic="Rank these",
            vote_type=VoteType.RANKING,
            options=["X", "Y", "Z"],
        )

        with pytest.raises(ValueError, match="all options"):
            manager.cast_vote(
                session.session_id,
                voter_id="agent-1",
                voter_name="Alice",
                choice=["X", "Y"],  # Missing Z
            )

    def test_change_vote(self, manager):
        """Test changing a vote."""
        session = manager.create_session(topic="Test")

        manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
        )

        updated = manager.change_vote(
            session.session_id,
            voter_id="agent-1",
            new_choice="reject",
            reason="Changed my mind",
        )

        assert updated.choice == "reject"

    def test_withdraw_vote(self, manager):
        """Test withdrawing a vote."""
        session = manager.create_session(topic="Test")

        manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
        )

        result = manager.withdraw_vote(session.session_id, "agent-1")
        assert result is True
        assert session.vote_count == 0

    def test_get_vote(self, manager):
        """Test getting a vote."""
        session = manager.create_session(topic="Test")

        manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
        )

        vote = manager.get_vote(session.session_id, "agent-1")
        assert vote is not None
        assert vote.choice == "approve"

    def test_has_voted(self, manager):
        """Test checking if voter has voted."""
        session = manager.create_session(topic="Test")

        assert manager.has_voted(session.session_id, "agent-1") is False

        manager.cast_vote(
            session.session_id,
            voter_id="agent-1",
            voter_name="Alice",
            choice="approve",
        )

        assert manager.has_voted(session.session_id, "agent-1") is True

    # -------------------------------------------------------------------------
    # Result Calculation Tests
    # -------------------------------------------------------------------------

    def test_calculate_approve_reject_passed(self, manager):
        """Test calculating approve/reject result - passed."""
        session = manager.create_session(
            topic="Test",
            eligible_voters={"a1", "a2", "a3"},
            pass_threshold=0.5,
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "approve")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "approve")
        manager.cast_vote(session.session_id, "a3", "Agent 3", "reject")

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.PASSED
        assert result["approve_count"] == 2
        assert result["reject_count"] == 1

    def test_calculate_approve_reject_rejected(self, manager):
        """Test calculating approve/reject result - rejected."""
        session = manager.create_session(
            topic="Test",
            eligible_voters={"a1", "a2", "a3"},
            pass_threshold=0.5,
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "reject")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "reject")
        manager.cast_vote(session.session_id, "a3", "Agent 3", "approve")

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.REJECTED
        assert result["approve_count"] == 1
        assert result["reject_count"] == 2

    def test_calculate_approve_reject_tie(self, manager):
        """Test calculating approve/reject result - tie."""
        session = manager.create_session(
            topic="Test",
            eligible_voters={"a1", "a2"},
            pass_threshold=0.5,
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "approve")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "reject")

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.TIE
        assert result["approve_ratio"] == 0.5

    def test_calculate_no_quorum(self, manager):
        """Test calculating result with no quorum."""
        session = manager.create_session(
            topic="Test",
            eligible_voters={"a1", "a2", "a3", "a4"},
            required_quorum=0.75,
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "approve")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "approve")
        # Only 2/4 = 50% participation, quorum is 75%

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.NO_QUORUM
        assert result["votes_received"] == 2

    def test_calculate_weighted_votes(self, manager):
        """Test calculating with weighted votes."""
        session = manager.create_session(
            topic="Test",
            eligible_voters={"a1", "a2"},
            pass_threshold=0.5,
        )

        # a1 has weight 3, a2 has weight 1
        manager.cast_vote(session.session_id, "a1", "Agent 1", "approve", weight=3.0)
        manager.cast_vote(session.session_id, "a2", "Agent 2", "reject", weight=1.0)

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.PASSED
        assert result["approve_weight"] == 3.0
        assert result["reject_weight"] == 1.0
        assert result["approve_ratio"] == 0.75

    def test_calculate_multiple_choice(self, manager):
        """Test calculating multiple choice result."""
        session = manager.create_session(
            topic="Choose one",
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=["A", "B", "C"],
            eligible_voters={"a1", "a2", "a3", "a4"},
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "A")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "B")
        manager.cast_vote(session.session_id, "a3", "Agent 3", "B")
        manager.cast_vote(session.session_id, "a4", "Agent 4", "C")

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.PASSED
        assert result["winner"] == "B"
        assert result["choice_counts"]["B"] == 2

    def test_calculate_multiple_choice_tie(self, manager):
        """Test calculating multiple choice with tie."""
        session = manager.create_session(
            topic="Choose one",
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=["A", "B"],
            eligible_voters={"a1", "a2"},
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "A")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "B")

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.TIE
        assert result["tie_options"] is not None

    def test_calculate_ranking(self, manager):
        """Test calculating ranking result (Borda count)."""
        session = manager.create_session(
            topic="Rank these",
            vote_type=VoteType.RANKING,
            options=["X", "Y", "Z"],
            eligible_voters={"a1", "a2", "a3"},
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", ["X", "Y", "Z"])
        manager.cast_vote(session.session_id, "a2", "Agent 2", ["X", "Z", "Y"])
        manager.cast_vote(session.session_id, "a3", "Agent 3", ["Y", "X", "Z"])

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.PASSED
        assert result["winner"] == "X"  # X has highest Borda score

    def test_calculate_score(self, manager):
        """Test calculating score voting result."""
        session = manager.create_session(
            topic="Rate this",
            vote_type=VoteType.SCORE,
            options=["1", "2", "3", "4", "5"],
            eligible_voters={"a1", "a2", "a3"},
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "5")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "4")
        manager.cast_vote(session.session_id, "a3", "Agent 3", "3")

        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.PASSED
        assert result["average_score"] == 4.0

    # -------------------------------------------------------------------------
    # Callback Tests
    # -------------------------------------------------------------------------

    def test_result_callback(self, manager):
        """Test result callback."""
        callback_called = [False]

        def on_result(session):
            callback_called[0] = True

        manager.on_result(on_result)

        session = manager.create_session(
            topic="Test",
            eligible_voters={"a1"},
        )
        manager.cast_vote(session.session_id, "a1", "Agent 1", "approve")
        manager.calculate_result(session.session_id)

        assert callback_called[0] is True

    # -------------------------------------------------------------------------
    # Statistics Tests
    # -------------------------------------------------------------------------

    def test_get_statistics(self, manager):
        """Test getting voting statistics."""
        session = manager.create_session(
            topic="Test",
            eligible_voters={"a1", "a2", "a3"},
        )

        manager.cast_vote(session.session_id, "a1", "Agent 1", "approve")
        manager.cast_vote(session.session_id, "a2", "Agent 2", "reject")

        stats = manager.get_statistics(session.session_id)

        assert stats["total_votes"] == 2
        assert stats["eligible_voters"] == 3
        assert stats["participation_rate"] == 2 / 3

    def test_get_statistics_nonexistent(self, manager):
        """Test getting statistics for non-existent session."""
        stats = manager.get_statistics(uuid4())
        assert stats == {}

    # -------------------------------------------------------------------------
    # Cleanup Tests
    # -------------------------------------------------------------------------

    def test_cleanup_expired(self, manager):
        """Test cleaning up expired sessions."""
        # Create expired session
        session = manager.create_session(
            topic="Expired",
            deadline_minutes=-1,  # Already expired
        )

        # Force the deadline to be in the past
        session.deadline = datetime.utcnow() - timedelta(minutes=5)

        count = manager.cleanup_expired()
        assert count == 1

        updated = manager.get_session(session.session_id)
        assert updated.status == VotingSessionStatus.EXPIRED

    def test_clear(self, manager):
        """Test clearing all sessions."""
        manager.create_session(topic="Test 1")
        manager.create_session(topic="Test 2")

        manager.clear()

        sessions = manager.list_sessions()
        assert len(sessions) == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestVotingIntegration:
    """Integration tests for voting."""

    def test_complete_voting_flow(self):
        """Test a complete voting flow."""
        manager = VotingManager()

        # Create session
        voters = {"alice", "bob", "charlie", "david"}
        session = manager.create_session(
            topic="Should we adopt the new policy?",
            description="Vote on the proposed policy change",
            vote_type=VoteType.APPROVE_REJECT,
            eligible_voters=voters,
            required_quorum=0.75,
            pass_threshold=0.6,
        )

        # Cast votes
        manager.cast_vote(session.session_id, "alice", "Alice", "approve", reason="Good idea")
        manager.cast_vote(session.session_id, "bob", "Bob", "approve")
        manager.cast_vote(session.session_id, "charlie", "Charlie", "reject", reason="Too risky")
        manager.cast_vote(session.session_id, "david", "David", "approve")

        # Calculate result
        result = manager.calculate_result(session.session_id)

        assert session.result == VoteResult.PASSED
        assert result["approve_count"] == 3
        assert result["reject_count"] == 1
        assert result["participation_rate"] == 1.0

    def test_multiple_choice_decision(self):
        """Test multiple choice decision process."""
        manager = VotingManager()

        # Create session
        session = manager.create_session(
            topic="Which framework should we use?",
            vote_type=VoteType.MULTIPLE_CHOICE,
            options=["React", "Vue", "Angular"],
            eligible_voters={"dev1", "dev2", "dev3", "dev4", "dev5"},
        )

        # Cast votes
        manager.cast_vote(session.session_id, "dev1", "Dev 1", "React")
        manager.cast_vote(session.session_id, "dev2", "Dev 2", "React")
        manager.cast_vote(session.session_id, "dev3", "Dev 3", "Vue")
        manager.cast_vote(session.session_id, "dev4", "Dev 4", "React")
        manager.cast_vote(session.session_id, "dev5", "Dev 5", "Angular")

        # Calculate result
        result = manager.calculate_result(session.session_id)

        assert result["winner"] == "React"
        assert result["choice_counts"]["React"] == 3

    def test_ranking_consensus(self):
        """Test ranking-based consensus building."""
        manager = VotingManager()

        # Create session for priority ranking
        session = manager.create_session(
            topic="Prioritize these features",
            vote_type=VoteType.RANKING,
            options=["Feature A", "Feature B", "Feature C", "Feature D"],
            eligible_voters={"pm", "dev", "design"},
        )

        # Cast ranking votes
        manager.cast_vote(session.session_id, "pm", "PM", ["Feature A", "Feature B", "Feature C", "Feature D"])
        manager.cast_vote(session.session_id, "dev", "Dev", ["Feature B", "Feature A", "Feature D", "Feature C"])
        manager.cast_vote(session.session_id, "design", "Design", ["Feature A", "Feature C", "Feature B", "Feature D"])

        # Calculate result
        result = manager.calculate_result(session.session_id)

        assert "final_ranking" in result
        assert "scores" in result
        # Feature A should rank highest

    def test_weighted_voting(self):
        """Test weighted voting based on expertise."""
        manager = VotingManager()

        # Create session with weighted voting
        session = manager.create_session(
            topic="Technical decision",
            vote_type=VoteType.APPROVE_REJECT,
            eligible_voters={"senior", "mid", "junior"},
            pass_threshold=0.5,
        )

        # Senior has more weight - weighted reject should win (4.0 > 3.0)
        manager.cast_vote(session.session_id, "senior", "Senior Dev", "reject", weight=4.0)
        manager.cast_vote(session.session_id, "mid", "Mid Dev", "approve", weight=2.0)
        manager.cast_vote(session.session_id, "junior", "Junior Dev", "approve", weight=1.0)

        # Calculate result
        result = manager.calculate_result(session.session_id)

        # Despite 2 approves vs 1 reject, weighted reject should win
        assert session.result == VoteResult.REJECTED
        assert result["reject_weight"] == 4.0
        assert result["approve_weight"] == 3.0  # 2.0 + 1.0
