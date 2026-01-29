"""
Swarm API Module

Provides REST API endpoints for Agent Swarm status monitoring.

Endpoints:
- GET /api/v1/swarm/{swarm_id} - Get swarm status
- GET /api/v1/swarm/{swarm_id}/workers - List all workers
- GET /api/v1/swarm/{swarm_id}/workers/{worker_id} - Get worker details
"""

from .routes import router

__all__ = ["router"]
