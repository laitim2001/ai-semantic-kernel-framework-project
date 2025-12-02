# =============================================================================
# IPA Platform - Dashboard API Routes
# =============================================================================
# Dashboard statistics endpoint for frontend
# =============================================================================

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_session
from src.infrastructure.database.models.workflow import Workflow
from src.infrastructure.database.models.execution import Execution
from src.infrastructure.database.models.agent import Agent
from src.infrastructure.database.models.checkpoint import Checkpoint


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class ExecutionChartData(BaseModel):
    """Execution chart data point."""
    date: str
    completed: int = 0
    failed: int = 0
    running: int = 0


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_workflows: int = 0
    active_workflows: int = 0
    total_agents: int = 0
    active_agents: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    pending_approvals: int = 0
    executions_today: int = 0
    success_rate: float = 0.0


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
) -> DashboardStats:
    """Get dashboard statistics."""
    try:
        # Get workflow counts
        workflow_result = await session.execute(
            select(func.count(Workflow.id))
        )
        total_workflows = workflow_result.scalar() or 0

        active_workflow_result = await session.execute(
            select(func.count(Workflow.id)).where(Workflow.status == "active")
        )
        active_workflows = active_workflow_result.scalar() or 0

        # Get agent counts
        agent_result = await session.execute(
            select(func.count(Agent.id))
        )
        total_agents = agent_result.scalar() or 0

        active_agent_result = await session.execute(
            select(func.count(Agent.id)).where(Agent.status == "active")
        )
        active_agents = active_agent_result.scalar() or 0

        # Get execution counts
        execution_result = await session.execute(
            select(func.count(Execution.id))
        )
        total_executions = execution_result.scalar() or 0

        successful_result = await session.execute(
            select(func.count(Execution.id)).where(Execution.status == "completed")
        )
        successful_executions = successful_result.scalar() or 0

        failed_result = await session.execute(
            select(func.count(Execution.id)).where(Execution.status == "failed")
        )
        failed_executions = failed_result.scalar() or 0

        # Get pending approvals
        pending_result = await session.execute(
            select(func.count(Checkpoint.id)).where(Checkpoint.status == "pending")
        )
        pending_approvals = pending_result.scalar() or 0

        # Get executions today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await session.execute(
            select(func.count(Execution.id)).where(Execution.created_at >= today_start)
        )
        executions_today = today_result.scalar() or 0

        # Calculate success rate
        success_rate = 0.0
        if total_executions > 0:
            success_rate = round((successful_executions / total_executions) * 100, 1)

        return DashboardStats(
            total_workflows=total_workflows,
            active_workflows=active_workflows,
            total_agents=total_agents,
            active_agents=active_agents,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            pending_approvals=pending_approvals,
            executions_today=executions_today,
            success_rate=success_rate,
        )

    except Exception as e:
        # Return empty stats on error (database might not have all tables)
        return DashboardStats()


@router.get("/executions/chart", response_model=List[ExecutionChartData])
async def get_execution_chart_data(
    days: int = 7,
    session: AsyncSession = Depends(get_session),
) -> List[ExecutionChartData]:
    """Get execution chart data for the last N days."""
    try:
        result = []
        today = datetime.utcnow().date()

        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            date_start = datetime.combine(date, datetime.min.time())
            date_end = datetime.combine(date, datetime.max.time())

            # Count completed executions for this day
            completed_result = await session.execute(
                select(func.count(Execution.id)).where(
                    Execution.created_at >= date_start,
                    Execution.created_at <= date_end,
                    Execution.status == "completed"
                )
            )
            completed = completed_result.scalar() or 0

            # Count failed executions for this day
            failed_result = await session.execute(
                select(func.count(Execution.id)).where(
                    Execution.created_at >= date_start,
                    Execution.created_at <= date_end,
                    Execution.status == "failed"
                )
            )
            failed = failed_result.scalar() or 0

            # Count running executions for this day
            running_result = await session.execute(
                select(func.count(Execution.id)).where(
                    Execution.created_at >= date_start,
                    Execution.created_at <= date_end,
                    Execution.status == "running"
                )
            )
            running = running_result.scalar() or 0

            result.append(ExecutionChartData(
                date=date.strftime("%m/%d"),
                completed=completed,
                failed=failed,
                running=running,
            ))

        return result

    except Exception as e:
        # Return empty chart data on error
        today = datetime.utcnow().date()
        return [
            ExecutionChartData(
                date=(today - timedelta(days=i)).strftime("%m/%d"),
                completed=0,
                failed=0,
                running=0,
            )
            for i in range(days - 1, -1, -1)
        ]
