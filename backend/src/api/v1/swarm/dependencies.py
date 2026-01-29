"""
Swarm API Dependencies

FastAPI dependencies for Swarm API endpoints.
"""

from fastapi import Depends

from src.integrations.swarm import SwarmTracker, get_swarm_tracker


def get_tracker() -> SwarmTracker:
    """Get the SwarmTracker instance.

    Returns:
        The global SwarmTracker instance.
    """
    return get_swarm_tracker()


# Type alias for dependency injection
TrackerDep = SwarmTracker
