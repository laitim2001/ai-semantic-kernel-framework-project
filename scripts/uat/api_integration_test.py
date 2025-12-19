"""
API Integration Test - Real HTTP Endpoint Testing

This script performs actual HTTP calls to the FastAPI backend
to verify API functionality end-to-end.

Usage:
    python scripts/uat/api_integration_test.py

Requirements:
    - FastAPI backend running at http://localhost:8000
    - PostgreSQL database connected
    - httpx installed (pip install httpx)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)


class APIIntegrationTest:
    """Real HTTP API Integration Test Runner"""

    BASE_URL = "http://localhost:8001"

    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.created_resources: Dict[str, List[str]] = {
            "workflows": [],
            "agents": [],
            "checkpoints": [],
            "handoffs": [],
            "groupchats": [],
            "sessions": [],
            "executions": []
        }
        self.test_id = 0
        self.start_time = datetime.now()
        # Store created agent ID for workflow tests
        self.test_agent_id: Optional[str] = None
        # Store created workflow ID for execution tests
        self.test_workflow_id: Optional[str] = None
        # Store created execution ID for checkpoint tests
        self.test_execution_id: Optional[str] = None
        # Store valid scenarios from routing API
        self.valid_scenarios: List[str] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all API integration tests"""
        print("\n" + "=" * 70)
        print("API Integration Test - Real HTTP Endpoint Testing")
        print("=" * 70)
        print(f"Base URL: {self.BASE_URL}")
        print(f"Started: {self.start_time.isoformat()}")
        print("=" * 70 + "\n")

        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0) as client:
            # Check server health first
            if not await self._check_server_health(client):
                return self._generate_report()

            # Phase 1: Agents API (FIRST - to get agent_id for workflows)
            print("\n--- Phase 1: Agents API ---")
            await self._test_agents_api(client)

            # Phase 2: Workflows API (uses agent_id from Phase 1)
            print("\n--- Phase 2: Workflows API ---")
            await self._test_workflows_api(client)

            # Phase 3: Checkpoints API
            print("\n--- Phase 3: Checkpoints API ---")
            await self._test_checkpoints_api(client)

            # Phase 4: Handoff API
            print("\n--- Phase 4: Handoff API ---")
            await self._test_handoff_api(client)

            # Phase 5: Routing API
            print("\n--- Phase 5: Routing API ---")
            await self._test_routing_api(client)

            # Phase 6: GroupChat API
            print("\n--- Phase 6: GroupChat API ---")
            await self._test_groupchat_api(client)

            # Cleanup created resources
            print("\n--- Cleanup ---")
            await self._cleanup_resources(client)

        return self._generate_report()

    async def _check_server_health(self, client: httpx.AsyncClient) -> bool:
        """Check if the API server is running"""
        print("Checking server health...")
        try:
            response = await client.get("/health")
            if response.status_code == 200:
                print(f"  [OK] Server is healthy: {response.json()}")
                return True
            else:
                print(f"  [FAIL] Server returned status {response.status_code}")
                self._record_result(
                    test_name="Server Health Check",
                    phase="Pre-flight",
                    method="GET",
                    endpoint="/health",
                    status="FAIL",
                    http_status=response.status_code,
                    error=f"Unexpected status code: {response.status_code}"
                )
                return False
        except httpx.ConnectError as e:
            print(f"  [FAIL] Cannot connect to server: {e}")
            self._record_result(
                test_name="Server Health Check",
                phase="Pre-flight",
                method="GET",
                endpoint="/health",
                status="FAIL",
                http_status=0,
                error=f"Connection error: {str(e)}"
            )
            return False

    # ========== Phase 2: Workflows API ==========

    async def _test_workflows_api(self, client: httpx.AsyncClient):
        """Test Workflows API endpoints"""

        # Test 2.1: Create Workflow
        # Using correct schema: WorkflowCreateRequest with graph_definition
        # Note: agent_id is a TOP-LEVEL field in the node, NOT inside config
        process_node = {
            "id": "process",
            "type": "agent",
            "name": "Process Node",
            "config": {}
        }
        # Add agent_id at node level (not in config)
        if self.test_agent_id:
            process_node["agent_id"] = self.test_agent_id

        workflow_data = {
            "name": f"Test Workflow {uuid4().hex[:8]}",
            "description": "Integration test workflow",
            "trigger_type": "manual",
            "trigger_config": {},
            "graph_definition": {
                "nodes": [
                    {"id": "start", "type": "start", "name": "Start Node", "config": {}},
                    process_node,
                    {"id": "end", "type": "end", "name": "End Node", "config": {}}
                ],
                "edges": [
                    {"source": "start", "target": "process"},
                    {"source": "process", "target": "end"}
                ],
                "variables": {}
            }
        }

        workflow_id = await self._test_create_resource(
            client=client,
            test_name="Create Workflow",
            phase="Phase 2: Workflows API",
            endpoint="/api/v1/workflows/",
            data=workflow_data,
            resource_type="workflows"
        )

        if workflow_id:
            # Store workflow_id for execution/checkpoint tests
            self.test_workflow_id = workflow_id
            # Test 2.2: List Workflows
            await self._test_list_resource(
                client=client,
                test_name="List Workflows",
                phase="Phase 2: Workflows API",
                endpoint="/api/v1/workflows/"
            )

            # Test 2.3: Get Single Workflow
            await self._test_get_resource(
                client=client,
                test_name="Get Workflow",
                phase="Phase 2: Workflows API",
                endpoint=f"/api/v1/workflows/{workflow_id}"
            )

            # Test 2.4: Validate Workflow
            await self._test_action(
                client=client,
                test_name="Validate Workflow",
                phase="Phase 2: Workflows API",
                method="POST",
                endpoint=f"/api/v1/workflows/{workflow_id}/validate",
                data={}
            )

            # Test 2.5: Update Workflow
            await self._test_update_resource(
                client=client,
                test_name="Update Workflow",
                phase="Phase 2: Workflows API",
                endpoint=f"/api/v1/workflows/{workflow_id}",
                data={"description": "Updated description"}
            )

    # ========== Phase 1: Agents API ==========

    async def _test_agents_api(self, client: httpx.AsyncClient):
        """Test Agents API endpoints"""

        # Test 1.1: Create Agent
        # Using correct schema: AgentCreateRequest with instructions (required)
        agent_data = {
            "name": f"Test Agent {uuid4().hex[:8]}",
            "description": "Integration test agent",
            "instructions": "You are a test assistant for integration testing.",
            "category": "testing",
            "tools": [],
            "model_config_data": {"temperature": 0.7, "max_tokens": 2000},
            "max_iterations": 10
        }

        agent_id = await self._test_create_resource(
            client=client,
            test_name="Create Agent",
            phase="Phase 1: Agents API",
            endpoint="/api/v1/agents/",
            data=agent_data,
            resource_type="agents"
        )

        if agent_id:
            # Store agent_id for workflow tests
            self.test_agent_id = agent_id

            # Test 1.2: List Agents
            await self._test_list_resource(
                client=client,
                test_name="List Agents",
                phase="Phase 1: Agents API",
                endpoint="/api/v1/agents/"
            )

            # Test 1.3: Get Single Agent (wait a bit for database commit)
            import asyncio
            await asyncio.sleep(0.1)  # Small delay to ensure commit

            await self._test_get_resource(
                client=client,
                test_name="Get Agent",
                phase="Phase 1: Agents API",
                endpoint=f"/api/v1/agents/{agent_id}"
            )

            # Test 1.4: Update Agent
            await self._test_update_resource(
                client=client,
                test_name="Update Agent",
                phase="Phase 1: Agents API",
                endpoint=f"/api/v1/agents/{agent_id}",
                data={"description": "Updated agent description"}
            )

    # ========== Phase 3: Checkpoints API ==========

    async def _test_checkpoints_api(self, client: httpx.AsyncClient):
        """Test Checkpoints API endpoints"""

        # First, create an execution record for checkpoint FK constraint
        # Checkpoints require a valid execution_id in the database
        execution_id = None
        if self.test_workflow_id:
            execution_data = {
                "workflow_id": self.test_workflow_id,
                "status": "running",
                "input_data": {"test": "checkpoint_test"}
            }
            execution_id = await self._test_create_resource(
                client=client,
                test_name="Create Execution for Checkpoints",
                phase="Phase 3: Checkpoints API",
                endpoint="/api/v1/executions/",
                data=execution_data,
                resource_type="executions"
            )
            if execution_id:
                self.test_execution_id = execution_id
                # Wait for database transaction to commit
                await asyncio.sleep(0.2)
        else:
            print("  [WARN] No workflow_id available, checkpoint tests may fail")

        # Use the created execution_id, or fallback (will fail FK constraint)
        test_execution_id = self.test_execution_id or str(uuid4())

        # Test 3.1: Create Checkpoint
        # Using correct schema: CheckpointCreateRequest with required fields:
        # - node_id, step (string), checkpoint_type, state (dict)
        checkpoint_data = {
            "execution_id": test_execution_id,
            "node_id": "approval_node",
            "step": "1",
            "checkpoint_type": "approval",
            "state": {"workflow_state": "in_progress", "previous_node": "start"},
            "payload": {
                "priority": "P1",
                "reason": "Integration test checkpoint"
            },
            "timeout_hours": 24,
            "notes": "Integration test checkpoint"
        }

        checkpoint_id = await self._test_create_resource(
            client=client,
            test_name="Create Checkpoint",
            phase="Phase 3: Checkpoints API",
            endpoint="/api/v1/checkpoints/",
            data=checkpoint_data,
            resource_type="checkpoints"
        )

        # Test 3.2: List Pending Checkpoints
        await self._test_list_resource(
            client=client,
            test_name="List Pending Checkpoints",
            phase="Phase 3: Checkpoints API",
            endpoint="/api/v1/checkpoints/pending"
        )

        if checkpoint_id:
            # Test 3.3: Get Checkpoint
            await self._test_get_resource(
                client=client,
                test_name="Get Checkpoint",
                phase="Phase 3: Checkpoints API",
                endpoint=f"/api/v1/checkpoints/{checkpoint_id}"
            )

            # Test 3.4: Approve Checkpoint
            # Note: user_id is now optional in schema to avoid FK constraint errors
            # When user_id is None, responded_by will not be set in database
            await self._test_action(
                client=client,
                test_name="Approve Checkpoint",
                phase="Phase 3: Checkpoints API",
                method="POST",
                endpoint=f"/api/v1/checkpoints/{checkpoint_id}/approve",
                data={
                    "response": {"action": "approved"},
                    "feedback": "Integration test approval"
                }
            )

        # Test 3.5: Create another checkpoint to test rejection
        # Reuse the same execution_id for FK constraint
        checkpoint_data2 = {
            "execution_id": test_execution_id,
            "node_id": "approval_node_2",
            "step": "2",
            "checkpoint_type": "review",
            "state": {"workflow_state": "in_progress"},
            "payload": {"priority": "P2", "reason": "Test rejection"},
            "timeout_hours": 24
        }

        checkpoint_id2 = await self._test_create_resource(
            client=client,
            test_name="Create Checkpoint for Rejection",
            phase="Phase 3: Checkpoints API",
            endpoint="/api/v1/checkpoints/",
            data=checkpoint_data2,
            resource_type="checkpoints"
        )

        if checkpoint_id2:
            # Test 3.6: Reject Checkpoint
            # Note: user_id is now optional in schema to avoid FK constraint errors
            # When user_id is None, responded_by will not be set in database
            await self._test_action(
                client=client,
                test_name="Reject Checkpoint",
                phase="Phase 3: Checkpoints API",
                method="POST",
                endpoint=f"/api/v1/checkpoints/{checkpoint_id2}/reject",
                data={
                    "reason": "Integration test rejection",
                    "response": {"action": "rejected"}
                }
            )

    # ========== Phase 4: Handoff API ==========

    async def _test_handoff_api(self, client: httpx.AsyncClient):
        """Test Handoff API endpoints"""

        # Test 4.1: Trigger Handoff
        # Using correct schema: HandoffTriggerRequest with source_agent_id (UUID)
        source_agent_uuid = str(uuid4())
        target_agent_uuid = str(uuid4())

        handoff_data = {
            "source_agent_id": source_agent_uuid,
            "target_agent_id": target_agent_uuid,
            "policy": "graceful",
            "context": {
                "ticket_id": f"TKT-TEST-{uuid4().hex[:6]}",
                "priority": "P1",
                "category": "Network"
            },
            "trigger_conditions": [],
            "required_capabilities": ["network_diagnosis"],
            "reason": "Integration test handoff",
            "metadata": {}
        }

        handoff_id = await self._test_create_resource(
            client=client,
            test_name="Trigger Handoff",
            phase="Phase 4: Handoff API",
            endpoint="/api/v1/handoff/trigger",
            data=handoff_data,
            resource_type="handoffs"
        )

        if handoff_id:
            # Test 4.2: Get Handoff Status
            await self._test_get_resource(
                client=client,
                test_name="Get Handoff Status",
                phase="Phase 4: Handoff API",
                endpoint=f"/api/v1/handoff/{handoff_id}/status"
            )

        # Test 4.3: Capability Matching
        # Using correct schema: CapabilityMatchRequest with requirements list
        await self._test_action(
            client=client,
            test_name="Capability Matching",
            phase="Phase 4: Handoff API",
            method="POST",
            endpoint="/api/v1/handoff/capability/match",
            data={
                "requirements": [
                    {
                        "capability_name": "network_diagnosis",
                        "min_proficiency": 0.5,
                        "required": True,
                        "weight": 1.0
                    },
                    {
                        "capability_name": "troubleshooting",
                        "min_proficiency": 0.3,
                        "required": False,
                        "weight": 0.5
                    }
                ],
                "strategy": "best_fit",
                "check_availability": True,
                "exclude_agents": [],
                "max_results": 10
            }
        )

        # Test 4.4: Get Handoff History
        await self._test_list_resource(
            client=client,
            test_name="Get Handoff History",
            phase="Phase 4: Handoff API",
            endpoint="/api/v1/handoff/history"
        )

    # ========== Phase 5: Routing API ==========

    async def _test_routing_api(self, client: httpx.AsyncClient):
        """Test Routing API endpoints"""

        # Test 5.1: Route to Scenario
        # Using correct schema: RouteRequest with source_scenario, target_scenario, source_execution_id
        # Valid scenarios: it_operations, customer_service, finance, hr, sales (see scenario_router.py)
        await self._test_action(
            client=client,
            test_name="Route to Scenario",
            phase="Phase 5: Routing API",
            method="POST",
            endpoint="/api/v1/routing/route",
            data={
                "source_scenario": "it_operations",
                "target_scenario": "customer_service",
                "source_execution_id": str(uuid4()),
                "data": {
                    "category": "Network",
                    "priority": "P1",
                    "department": "Finance",
                    "impact": "50 users"
                },
                "relation_type": "routed_to",
                "metadata": {}
            }
        )

        # Test 5.2: List Scenarios
        await self._test_list_resource(
            client=client,
            test_name="List Scenarios",
            phase="Phase 5: Routing API",
            endpoint="/api/v1/routing/scenarios"
        )

        # Test 5.3: Routing Health Check
        await self._test_get_resource(
            client=client,
            test_name="Routing Health Check",
            phase="Phase 5: Routing API",
            endpoint="/api/v1/routing/health"
        )

    # ========== Phase 6: GroupChat API ==========

    async def _test_groupchat_api(self, client: httpx.AsyncClient):
        """Test GroupChat API endpoints"""

        # Test 6.1: Create GroupChat
        # Using correct schema: CreateGroupChatRequest with agent_ids (not participants)
        # Use the agent_id from Phase 1 if available, otherwise use placeholder IDs
        agent_ids = ["network_expert", "endpoint_expert", "helpdesk_agent"]
        if self.test_agent_id:
            agent_ids = [self.test_agent_id, f"agent_{uuid4().hex[:8]}", f"agent_{uuid4().hex[:8]}"]

        groupchat_data = {
            "name": f"Test GroupChat {uuid4().hex[:8]}",
            "description": "Integration test group chat",
            "agent_ids": agent_ids,
            "config": {
                "max_rounds": 10,
                "speaker_selection_method": "round_robin",
                "allow_repeat_speaker": False
            }
        }

        groupchat_id = await self._test_create_resource(
            client=client,
            test_name="Create GroupChat",
            phase="Phase 6: GroupChat API",
            endpoint="/api/v1/groupchat/",
            data=groupchat_data,
            resource_type="groupchats"
        )

        # Test 6.2: List GroupChats
        await self._test_list_resource(
            client=client,
            test_name="List GroupChats",
            phase="Phase 6: GroupChat API",
            endpoint="/api/v1/groupchat/"
        )

        if groupchat_id:
            # Test 6.3: Get GroupChat
            await self._test_get_resource(
                client=client,
                test_name="Get GroupChat",
                phase="Phase 6: GroupChat API",
                endpoint=f"/api/v1/groupchat/{groupchat_id}"
            )

            # Test 6.4: Create Session
            # Using correct schema: CreateSessionRequest with user_id (required)
            session_data = {
                "user_id": f"user-{uuid4().hex[:8]}",
                "initial_context": {
                    "topic": "Integration test discussion"
                },
                "session_timeout_minutes": 30,
                "max_turns": 50
            }

            session_id = await self._test_create_resource(
                client=client,
                test_name="Create GroupChat Session",
                phase="Phase 6: GroupChat API",
                endpoint="/api/v1/groupchat/sessions/",
                data=session_data,
                resource_type="sessions"
            )

    # ========== Helper Methods ==========

    async def _test_create_resource(
        self,
        client: httpx.AsyncClient,
        test_name: str,
        phase: str,
        endpoint: str,
        data: Dict[str, Any],
        resource_type: str
    ) -> Optional[str]:
        """Test creating a resource and return its ID"""
        start = datetime.now()
        try:
            response = await client.post(endpoint, json=data)
            duration = (datetime.now() - start).total_seconds() * 1000

            if response.status_code in [200, 201]:
                result = response.json()
                resource_id = result.get("id") or result.get("data", {}).get("id")

                if resource_id:
                    self.created_resources[resource_type].append(str(resource_id))

                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="POST",
                    endpoint=endpoint,
                    status="PASS",
                    http_status=response.status_code,
                    duration_ms=duration,
                    response=result
                )
                print(f"  [PASS] {test_name} (HTTP {response.status_code}, {duration:.1f}ms)")
                return str(resource_id) if resource_id else None
            else:
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="POST",
                    endpoint=endpoint,
                    status="FAIL",
                    http_status=response.status_code,
                    duration_ms=duration,
                    error=response.text
                )
                print(f"  [FAIL] {test_name} (HTTP {response.status_code})")
                return None

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self._record_result(
                test_name=test_name,
                phase=phase,
                method="POST",
                endpoint=endpoint,
                status="FAIL",
                http_status=0,
                duration_ms=duration,
                error=str(e)
            )
            print(f"  [FAIL] {test_name} (Exception: {e})")
            return None

    async def _test_list_resource(
        self,
        client: httpx.AsyncClient,
        test_name: str,
        phase: str,
        endpoint: str
    ):
        """Test listing resources"""
        start = datetime.now()
        try:
            response = await client.get(endpoint)
            duration = (datetime.now() - start).total_seconds() * 1000

            if response.status_code == 200:
                result = response.json()
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="GET",
                    endpoint=endpoint,
                    status="PASS",
                    http_status=response.status_code,
                    duration_ms=duration,
                    response={"count": len(result) if isinstance(result, list) else "N/A"}
                )
                print(f"  [PASS] {test_name} (HTTP {response.status_code}, {duration:.1f}ms)")
            else:
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="GET",
                    endpoint=endpoint,
                    status="FAIL",
                    http_status=response.status_code,
                    duration_ms=duration,
                    error=response.text
                )
                print(f"  [FAIL] {test_name} (HTTP {response.status_code})")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self._record_result(
                test_name=test_name,
                phase=phase,
                method="GET",
                endpoint=endpoint,
                status="FAIL",
                http_status=0,
                duration_ms=duration,
                error=str(e)
            )
            print(f"  [FAIL] {test_name} (Exception: {e})")

    async def _test_get_resource(
        self,
        client: httpx.AsyncClient,
        test_name: str,
        phase: str,
        endpoint: str
    ):
        """Test getting a single resource"""
        start = datetime.now()
        try:
            response = await client.get(endpoint)
            duration = (datetime.now() - start).total_seconds() * 1000

            if response.status_code == 200:
                result = response.json()
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="GET",
                    endpoint=endpoint,
                    status="PASS",
                    http_status=response.status_code,
                    duration_ms=duration,
                    response=result
                )
                print(f"  [PASS] {test_name} (HTTP {response.status_code}, {duration:.1f}ms)")
            else:
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="GET",
                    endpoint=endpoint,
                    status="FAIL",
                    http_status=response.status_code,
                    duration_ms=duration,
                    error=response.text
                )
                print(f"  [FAIL] {test_name} (HTTP {response.status_code})")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self._record_result(
                test_name=test_name,
                phase=phase,
                method="GET",
                endpoint=endpoint,
                status="FAIL",
                http_status=0,
                duration_ms=duration,
                error=str(e)
            )
            print(f"  [FAIL] {test_name} (Exception: {e})")

    async def _test_update_resource(
        self,
        client: httpx.AsyncClient,
        test_name: str,
        phase: str,
        endpoint: str,
        data: Dict[str, Any]
    ):
        """Test updating a resource"""
        start = datetime.now()
        try:
            response = await client.put(endpoint, json=data)
            duration = (datetime.now() - start).total_seconds() * 1000

            if response.status_code == 200:
                result = response.json()
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="PUT",
                    endpoint=endpoint,
                    status="PASS",
                    http_status=response.status_code,
                    duration_ms=duration,
                    response=result
                )
                print(f"  [PASS] {test_name} (HTTP {response.status_code}, {duration:.1f}ms)")
            else:
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method="PUT",
                    endpoint=endpoint,
                    status="FAIL",
                    http_status=response.status_code,
                    duration_ms=duration,
                    error=response.text
                )
                print(f"  [FAIL] {test_name} (HTTP {response.status_code})")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self._record_result(
                test_name=test_name,
                phase=phase,
                method="PUT",
                endpoint=endpoint,
                status="FAIL",
                http_status=0,
                duration_ms=duration,
                error=str(e)
            )
            print(f"  [FAIL] {test_name} (Exception: {e})")

    async def _test_action(
        self,
        client: httpx.AsyncClient,
        test_name: str,
        phase: str,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Test an action endpoint"""
        start = datetime.now()
        try:
            if method == "POST":
                response = await client.post(endpoint, json=data or {})
            elif method == "DELETE":
                response = await client.delete(endpoint)
            else:
                response = await client.get(endpoint)

            duration = (datetime.now() - start).total_seconds() * 1000

            if response.status_code in [200, 201, 204]:
                try:
                    result = response.json() if response.text else {}
                except:
                    result = {}

                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method=method,
                    endpoint=endpoint,
                    status="PASS",
                    http_status=response.status_code,
                    duration_ms=duration,
                    response=result
                )
                print(f"  [PASS] {test_name} (HTTP {response.status_code}, {duration:.1f}ms)")
            else:
                self._record_result(
                    test_name=test_name,
                    phase=phase,
                    method=method,
                    endpoint=endpoint,
                    status="FAIL",
                    http_status=response.status_code,
                    duration_ms=duration,
                    error=response.text
                )
                print(f"  [FAIL] {test_name} (HTTP {response.status_code})")

        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self._record_result(
                test_name=test_name,
                phase=phase,
                method=method,
                endpoint=endpoint,
                status="FAIL",
                http_status=0,
                duration_ms=duration,
                error=str(e)
            )
            print(f"  [FAIL] {test_name} (Exception: {e})")

    async def _cleanup_resources(self, client: httpx.AsyncClient):
        """Clean up all created resources"""
        print("Cleaning up created resources...")

        # Delete in reverse dependency order
        cleanup_order = [
            ("sessions", "/api/v1/groupchat/sessions/"),
            ("groupchats", "/api/v1/groupchat/"),
            ("handoffs", "/api/v1/handoff/"),
            ("checkpoints", "/api/v1/checkpoints/"),
            ("agents", "/api/v1/agents/"),
            ("workflows", "/api/v1/workflows/")
        ]

        for resource_type, base_endpoint in cleanup_order:
            for resource_id in self.created_resources.get(resource_type, []):
                try:
                    endpoint = f"{base_endpoint}{resource_id}"
                    response = await client.delete(endpoint)
                    if response.status_code in [200, 204, 404]:
                        print(f"  Deleted {resource_type}/{resource_id}")
                except Exception as e:
                    print(f"  Failed to delete {resource_type}/{resource_id}: {e}")

    def _record_result(
        self,
        test_name: str,
        phase: str,
        method: str,
        endpoint: str,
        status: str,
        http_status: int,
        duration_ms: float = 0,
        response: Optional[Dict[str, Any]] = None,
        error: str = ""
    ):
        """Record a test result"""
        self.test_id += 1
        self.results.append({
            "test_id": self.test_id,
            "test_name": test_name,
            "phase": phase,
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "http_status": http_status,
            "duration_ms": round(duration_ms, 2),
            "response": response or {},
            "error": error
        })

    def _generate_report(self) -> Dict[str, Any]:
        """Generate the final test report"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = len(self.results)
        pass_rate = f"{(passed / total * 100):.1f}%" if total > 0 else "0%"

        report = {
            "test_plan": "API Integration Test",
            "executed_at": self.start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "environment": {
                "base_url": self.BASE_URL,
                "test_type": "HTTP API Integration"
            },
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": pass_rate,
                "total_duration_seconds": round(total_duration, 2)
            },
            "results": self.results
        }

        # Print summary
        print("\n" + "=" * 70)
        print("Test Summary")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass Rate: {pass_rate}")
        print(f"Duration: {total_duration:.2f} seconds")
        print("=" * 70)

        return report


def save_results(report: Dict[str, Any]):
    """Save test results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure sessions directory exists
    sessions_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "claudedocs", "uat", "sessions"
    )
    os.makedirs(sessions_dir, exist_ok=True)

    filename = os.path.join(sessions_dir, f"api_integration_{timestamp}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {filename}")
    return filename


async def main():
    """Main entry point"""
    test_runner = APIIntegrationTest()
    report = await test_runner.run_all_tests()
    result_file = save_results(report)

    # Return exit code based on results
    if report["summary"]["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
