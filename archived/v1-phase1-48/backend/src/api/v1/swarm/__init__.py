"""
Swarm API Module

Provides REST API endpoints for Agent Swarm status monitoring.

Endpoints:
- GET /api/v1/swarm/{swarm_id} - Get swarm status
- GET /api/v1/swarm/{swarm_id}/workers - List all workers
- GET /api/v1/swarm/{swarm_id}/workers/{worker_id} - Get worker details

Demo Endpoints:
- POST /api/v1/swarm/demo/start - Start a demo swarm execution
- GET /api/v1/swarm/demo/status/{swarm_id} - Get demo status
- POST /api/v1/swarm/demo/stop/{swarm_id} - Stop a demo
- GET /api/v1/swarm/demo/scenarios - List available scenarios
"""

from .routes import router
from .demo import router as demo_router

__all__ = ["router", "demo_router"]
