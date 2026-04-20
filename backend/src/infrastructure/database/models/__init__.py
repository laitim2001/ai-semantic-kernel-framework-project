# =============================================================================
# IPA Platform - Database Models
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
#
# This module contains SQLAlchemy ORM models for the IPA Platform.
# All models use UUID primary keys and include audit timestamps.
#
# Models:
#   - User: Platform users with role-based access
#   - Agent: AI Agent definitions with instructions and tools
#   - Workflow: Workflow definitions with graph structure
#   - Execution: Workflow execution records with statistics
#   - Checkpoint: Human-in-the-loop checkpoint states
#   - AuditLog: Complete audit trail for compliance
# =============================================================================

from src.infrastructure.database.models.agent import Agent
from src.infrastructure.database.models.agent_expert import AgentExpert  # Sprint 163
from src.infrastructure.database.models.audit import AuditLog
from src.infrastructure.database.models.base import Base, TimestampMixin, UUIDMixin
from src.infrastructure.database.models.checkpoint import Checkpoint
from src.infrastructure.database.models.execution import Execution
from src.infrastructure.database.models.orchestration_execution_log import (
    OrchestrationExecutionLog,  # Sprint 169
)
from src.infrastructure.database.models.session import AttachmentModel, MessageModel, SessionModel
from src.infrastructure.database.models.session_memory import SessionMemory  # Sprint 172
from src.infrastructure.database.models.user import User
from src.infrastructure.database.models.workflow import Workflow

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "User",
    "Agent",
    "AgentExpert",
    "Workflow",
    "Execution",
    "Checkpoint",
    "AuditLog",
    "SessionModel",
    "MessageModel",
    "AttachmentModel",
    "OrchestrationExecutionLog",
    "SessionMemory",
]
