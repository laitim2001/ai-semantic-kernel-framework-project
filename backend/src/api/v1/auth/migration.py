# =============================================================================
# IPA Platform - Guest Data Migration API
# =============================================================================
# Sprint 72: S72-2 - Guest Data Migration API
# Phase 18: Authentication System
#
# API endpoint to migrate guest user data to authenticated user.
# Migrates sessions and sandbox directories.
#
# Dependencies:
#   - SessionService (src.domain.sessions.service)
#   - SandboxConfig (src.core.sandbox_config)
# =============================================================================

import logging
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_user
from src.infrastructure.database import get_session
from src.infrastructure.database.models.user import User
from src.infrastructure.database.models.session import SessionModel

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class MigrateGuestRequest(BaseModel):
    """Request body for guest data migration."""
    guest_id: str = Field(..., description="Guest user ID to migrate from")


class MigrateGuestResponse(BaseModel):
    """Response for guest data migration."""
    success: bool
    sessions_migrated: int
    directories_migrated: List[str]
    message: str


# =============================================================================
# Sandbox Directory Helper
# =============================================================================


def get_sandbox_base_dir() -> Path:
    """Get base directory for sandbox data."""
    # Default to data/ in project root
    from src.core.config import get_settings
    settings = get_settings()
    return Path(getattr(settings, 'data_dir', 'data'))


def get_user_sandbox_dir(user_id: str, dir_type: str) -> Path:
    """Get user-specific sandbox directory.

    Args:
        user_id: User ID (guest-xxx or UUID)
        dir_type: Directory type (uploads, sandbox, outputs)

    Returns:
        Path to user's directory for the given type
    """
    base_dir = get_sandbox_base_dir()
    return base_dir / dir_type / user_id


# =============================================================================
# Routes
# =============================================================================


@router.post(
    "/migrate-guest",
    response_model=MigrateGuestResponse,
    summary="Migrate guest data to authenticated user",
    description="Migrate sessions and sandbox directories from guest ID to current user.",
)
async def migrate_guest_data(
    data: MigrateGuestRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MigrateGuestResponse:
    """
    Migrate guest user data to authenticated user.

    This endpoint:
    1. Updates all sessions from guest_user_id to user_id
    2. Moves sandbox directories (uploads, sandbox, outputs)
    3. Cleans up empty guest directories

    Called on first login after guest usage.
    """
    guest_id = data.guest_id
    user_id = str(current_user.id)

    logger.info(f"Migrating guest data: {guest_id} -> {user_id}")

    # Skip if trying to migrate to self
    if guest_id == user_id:
        return MigrateGuestResponse(
            success=True,
            sessions_migrated=0,
            directories_migrated=[],
            message="No migration needed (same user)",
        )

    # 1. Migrate sessions in database
    sessions_migrated = await _migrate_sessions(session, guest_id, user_id)

    # 2. Migrate sandbox directories
    directories_migrated = _migrate_sandbox_directories(guest_id, user_id)

    logger.info(
        f"Migration complete: {sessions_migrated} sessions, "
        f"{len(directories_migrated)} directories migrated"
    )

    return MigrateGuestResponse(
        success=True,
        sessions_migrated=sessions_migrated,
        directories_migrated=directories_migrated,
        message=f"Successfully migrated data from guest {guest_id}",
    )


async def _migrate_sessions(
    db: AsyncSession,
    guest_id: str,
    user_id: str,
) -> int:
    """Migrate sessions from guest to authenticated user.

    Updates sessions that have guest_user_id matching the guest_id
    to use the authenticated user's ID.

    Args:
        db: Database session
        guest_id: Guest user ID to migrate from
        user_id: Authenticated user ID to migrate to

    Returns:
        Number of sessions migrated
    """
    from sqlalchemy import select, update
    from uuid import UUID

    try:
        # Find sessions with this guest_id
        result = await db.execute(
            select(SessionModel).where(SessionModel.guest_user_id == guest_id)
        )
        sessions = result.scalars().all()

        if not sessions:
            logger.info(f"No sessions found for guest {guest_id}")
            return 0

        # Update sessions to use authenticated user
        user_uuid = UUID(user_id)
        await db.execute(
            update(SessionModel)
            .where(SessionModel.guest_user_id == guest_id)
            .values(
                user_id=user_uuid,
                guest_user_id=None,  # Clear guest ID after migration
            )
        )

        await db.commit()

        count = len(sessions)
        logger.info(f"Migrated {count} sessions from guest {guest_id} to user {user_id}")
        return count

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to migrate sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to migrate sessions: {str(e)}",
        )


def _migrate_sandbox_directories(guest_id: str, user_id: str) -> List[str]:
    """Migrate sandbox directories from guest to user.

    Moves files from guest directories to user directories for:
    - uploads/
    - sandbox/
    - outputs/

    Args:
        guest_id: Guest user ID
        user_id: Authenticated user ID

    Returns:
        List of directory types that were migrated
    """
    migrated = []
    dir_types = ["uploads", "sandbox", "outputs"]

    for dir_type in dir_types:
        guest_dir = get_user_sandbox_dir(guest_id, dir_type)
        user_dir = get_user_sandbox_dir(user_id, dir_type)

        if not guest_dir.exists():
            logger.debug(f"Guest directory does not exist: {guest_dir}")
            continue

        try:
            # Create user directory if needed
            user_dir.mkdir(parents=True, exist_ok=True)

            # Move all files from guest to user directory
            file_count = 0
            for item in guest_dir.iterdir():
                dest = user_dir / item.name

                # Handle name conflicts by adding suffix
                if dest.exists():
                    base = dest.stem
                    suffix = dest.suffix
                    counter = 1
                    while dest.exists():
                        dest = user_dir / f"{base}_{counter}{suffix}"
                        counter += 1

                shutil.move(str(item), str(dest))
                file_count += 1

            # Remove empty guest directory
            if guest_dir.exists() and not any(guest_dir.iterdir()):
                guest_dir.rmdir()
                logger.debug(f"Removed empty guest directory: {guest_dir}")

            if file_count > 0:
                migrated.append(dir_type)
                logger.info(f"Migrated {file_count} files from {dir_type}/{guest_id} to {dir_type}/{user_id}")

        except Exception as e:
            logger.warning(f"Failed to migrate {dir_type} directory: {e}")
            # Continue with other directories even if one fails

    return migrated
