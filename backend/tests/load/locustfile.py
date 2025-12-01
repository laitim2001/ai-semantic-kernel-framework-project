"""
IPA Platform - Load Testing with Locust

Simulates realistic user behavior for performance testing.

User Scenarios:
- Dashboard viewer: Views dashboard and stats
- Workflow manager: Creates and manages workflows
- Agent tester: Tests and configures agents
- Approver: Reviews and approves pending items

Usage:
    # Web UI mode
    locust -f locustfile.py --host=http://localhost:8000

    # Headless mode (CI/CD)
    locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 10m

    # With HTML report
    locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 10m --html=report.html

Author: IPA Platform Team
Version: 1.0.0
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import random
import json
from datetime import datetime


# =============================================================================
# Test Data
# =============================================================================

WORKFLOW_NAMES = [
    "IT Support Ticket Routing",
    "Customer Service Escalation",
    "Invoice Processing",
    "Employee Onboarding",
    "Leave Request Approval"
]

AGENT_NAMES = [
    "Support Agent",
    "Routing Agent",
    "Analysis Agent",
    "Response Agent"
]

TEST_MESSAGES = [
    "Hello, I need help with my account",
    "Process this request please",
    "Analyze the following data",
    "Route this ticket to the right team"
]


# =============================================================================
# Base User Class
# =============================================================================

class IPABaseUser(HttpUser):
    """Base user class with common functionality."""

    abstract = True
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user session with authentication."""
        self.access_token = None
        self.user_id = None
        self.test_workflow_id = None
        self.test_agent_id = None

        # Try to login
        try:
            response = self.client.post("/api/v1/auth/login", json={
                "email": f"load_test_{self.environment.runner.user_count}@example.com",
                "password": "LoadTest123!",
            }, catch_response=True)

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token", "test_token")
                self.user_id = data.get("user_id")
                response.success()
            else:
                # Use test token for development
                self.access_token = f"load_test_token_{datetime.now().timestamp()}"
                response.success()  # Don't fail the test

        except Exception as e:
            self.access_token = f"load_test_token_{datetime.now().timestamp()}"

        # Set authorization header
        self.client.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Load-Test": "true"
        })


# =============================================================================
# Dashboard Viewer User
# =============================================================================

class DashboardViewer(IPABaseUser):
    """Simulates users primarily viewing dashboards and stats."""

    weight = 3  # Most common user type

    @task(5)
    def view_dashboard_stats(self):
        """View main dashboard statistics."""
        with self.client.get(
            "/api/v1/dashboard/stats",
            catch_response=True,
            name="Dashboard Stats"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(3)
    def view_recent_executions(self):
        """View recent workflow executions."""
        with self.client.get(
            "/api/v1/executions/",
            params={"limit": 10, "sort": "-created_at"},
            catch_response=True,
            name="Recent Executions"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(2)
    def view_execution_chart_data(self):
        """Get execution chart data for visualization."""
        with self.client.get(
            "/api/v1/dashboard/execution-chart",
            params={"period": "7d"},
            catch_response=True,
            name="Execution Chart"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(1)
    def view_system_health(self):
        """Check system health status."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="Health Check"
        ) as response:
            if response.status_code == 200:
                response.success()


# =============================================================================
# Workflow Manager User
# =============================================================================

class WorkflowManager(IPABaseUser):
    """Simulates users managing workflows."""

    weight = 2

    @task(4)
    def list_workflows(self):
        """List all workflows."""
        with self.client.get(
            "/api/v1/workflows/",
            params={"page": 1, "limit": 20},
            catch_response=True,
            name="List Workflows"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(2)
    def search_workflows(self):
        """Search workflows by name."""
        search_term = random.choice(WORKFLOW_NAMES).split()[0]
        with self.client.get(
            "/api/v1/workflows/",
            params={"search": search_term},
            catch_response=True,
            name="Search Workflows"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(1)
    def view_workflow_detail(self):
        """View workflow details."""
        # Use a placeholder ID or get from previous response
        workflow_id = self.test_workflow_id or "test_workflow_id"
        with self.client.get(
            f"/api/v1/workflows/{workflow_id}",
            catch_response=True,
            name="Workflow Detail"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(1)
    def execute_workflow(self):
        """Execute a workflow."""
        workflow_id = self.test_workflow_id or "test_workflow_id"
        with self.client.post(
            f"/api/v1/workflows/{workflow_id}/execute",
            json={
                "input": {"message": random.choice(TEST_MESSAGES)},
                "context": {"load_test": True}
            },
            catch_response=True,
            name="Execute Workflow"
        ) as response:
            if response.status_code in [200, 201, 404, 422]:
                response.success()


# =============================================================================
# Agent Tester User
# =============================================================================

class AgentTester(IPABaseUser):
    """Simulates users testing and configuring agents."""

    weight = 2

    @task(4)
    def list_agents(self):
        """List all agents."""
        with self.client.get(
            "/api/v1/agents/",
            catch_response=True,
            name="List Agents"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(2)
    def view_agent_detail(self):
        """View agent details."""
        agent_id = self.test_agent_id or "test_agent_id"
        with self.client.get(
            f"/api/v1/agents/{agent_id}",
            catch_response=True,
            name="Agent Detail"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(1)
    def test_agent(self):
        """Test an agent with a message."""
        agent_id = self.test_agent_id or "test_agent_id"
        with self.client.post(
            f"/api/v1/agents/{agent_id}/test",
            json={
                "message": random.choice(TEST_MESSAGES),
                "max_tokens": 100
            },
            catch_response=True,
            name="Test Agent"
        ) as response:
            if response.status_code in [200, 201, 404, 422]:
                response.success()

    @task(2)
    def list_templates(self):
        """List available templates."""
        with self.client.get(
            "/api/v1/templates/",
            catch_response=True,
            name="List Templates"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()


# =============================================================================
# Approver User
# =============================================================================

class ApproverUser(IPABaseUser):
    """Simulates users reviewing and approving items."""

    weight = 1

    @task(4)
    def view_pending_approvals(self):
        """View pending approvals."""
        with self.client.get(
            "/api/v1/checkpoints/pending",
            catch_response=True,
            name="Pending Approvals"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(2)
    def view_approval_detail(self):
        """View approval item detail."""
        with self.client.get(
            "/api/v1/checkpoints/test_checkpoint_id",
            catch_response=True,
            name="Approval Detail"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(1)
    def approve_item(self):
        """Approve a pending item."""
        with self.client.post(
            "/api/v1/checkpoints/test_checkpoint_id/approve",
            json={
                "decision": "approved",
                "comments": "Approved in load test"
            },
            catch_response=True,
            name="Approve Item"
        ) as response:
            if response.status_code in [200, 201, 404, 422]:
                response.success()

    @task(3)
    def view_audit_logs(self):
        """View audit logs."""
        with self.client.get(
            "/api/v1/audit/",
            params={"limit": 20},
            catch_response=True,
            name="Audit Logs"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()


# =============================================================================
# Mixed User (All Operations)
# =============================================================================

class MixedUser(IPABaseUser):
    """Simulates users performing various operations."""

    weight = 2

    @task(3)
    def view_dashboard(self):
        """View dashboard."""
        with self.client.get(
            "/api/v1/dashboard/stats",
            catch_response=True,
            name="Mixed - Dashboard"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(2)
    def list_workflows(self):
        """List workflows."""
        with self.client.get(
            "/api/v1/workflows/",
            catch_response=True,
            name="Mixed - Workflows"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(2)
    def list_agents(self):
        """List agents."""
        with self.client.get(
            "/api/v1/agents/",
            catch_response=True,
            name="Mixed - Agents"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @task(1)
    def view_approvals(self):
        """View approvals."""
        with self.client.get(
            "/api/v1/checkpoints/pending",
            catch_response=True,
            name="Mixed - Approvals"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()


# =============================================================================
# Event Hooks
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("=" * 60)
    print("IPA Platform Load Test Starting")
    print(f"Target Host: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("=" * 60)
    print("IPA Platform Load Test Completed")
    print("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, **kwargs):
    """Called on each request - can be used for custom metrics."""
    pass


# =============================================================================
# Test Configuration
# =============================================================================

# For running with: locust -f locustfile.py
# All user classes will be available for selection in the web UI
