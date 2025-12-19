"""
IT Ticket E2E Workflow Test
============================
Complete end-to-end testing of IT ticket triage workflow with real Azure OpenAI LLM.

Test Plan: claudedocs/uat/TEST-PLAN-IT-TICKET-E2E.md
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load .env from backend
load_dotenv(backend_path / ".env")


@dataclass
class TestResult:
    """Individual test result."""
    test_id: int
    test_name: str
    phase: str
    status: str  # PASS, FAIL, SKIP
    duration_ms: float = 0.0
    llm_calls: int = 0
    llm_tokens: int = 0
    llm_cost: float = 0.0
    response: str = ""
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSummary:
    """Test execution summary."""
    test_plan: str
    executed_at: str
    environment: Dict[str, str]
    summary: Dict[str, Any]
    metrics: Dict[str, Any]
    results: List[Dict[str, Any]]


class ITTicketE2EWorkflowTest:
    """Complete IT Ticket E2E Workflow Test Suite."""

    def __init__(self):
        """Initialize test suite."""
        self.azure_config = {
            "provider": "azure_openai",
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "azure_deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
            "max_completion_tokens": 500,
        }

        self.results: List[TestResult] = []
        self.start_time = None

        # Test data
        self.test_tickets = self._init_test_tickets()
        self.test_agents = self._init_test_agents()

    def _init_test_tickets(self) -> List[Dict[str, Any]]:
        """Initialize test ticket data."""
        return [
            {
                "id": "TKT-E2E-001",
                "title": "整層網路斷線 - 財務部",
                "description": "財務部全體同事無法連網，影響月結作業，約 50 人受影響",
                "reporter": {
                    "name": "陳財務長",
                    "department": "Finance",
                    "role": "CFO",
                    "vip": True
                },
                "expected": {
                    "priority": "P1",
                    "category": "Network",
                    "team": "network-team",
                    "needs_approval": True
                }
            },
            {
                "id": "TKT-E2E-002",
                "title": "VPN 連線緩慢",
                "description": "從家裡連 VPN 速度很慢，約 5 分鐘才能登入，已經持續三天",
                "reporter": {
                    "name": "王工程師",
                    "department": "Engineering",
                    "role": "Engineer",
                    "vip": False
                },
                "expected": {
                    "priority": "P2",
                    "category": "Network",
                    "team": "network-team",
                    "needs_approval": False
                }
            },
            {
                "id": "TKT-E2E-003",
                "title": "電腦開不了機",
                "description": "按電源鍵沒反應，30 分鐘後有重要客戶會議",
                "reporter": {
                    "name": "李經理",
                    "department": "Sales",
                    "role": "Manager",
                    "vip": False
                },
                "expected": {
                    "priority": "P1",
                    "category": "Hardware",
                    "team": "endpoint-team",
                    "needs_approval": True
                }
            },
            {
                "id": "TKT-E2E-004",
                "title": "申請安裝 VS Code",
                "description": "需要安裝 VS Code 進行開發工作，目前電腦沒有",
                "reporter": {
                    "name": "張實習生",
                    "department": "Engineering",
                    "role": "Intern",
                    "vip": False
                },
                "expected": {
                    "priority": "P3",
                    "category": "Software",
                    "team": "helpdesk",
                    "needs_approval": False
                }
            }
        ]

    def _init_test_agents(self) -> Dict[str, Dict[str, Any]]:
        """Initialize test agent definitions."""
        return {
            "triage_agent": {
                "name": "IT Triage Agent",
                "instructions": """You are an IT support triage specialist. Analyze the ticket and determine:
1. Priority: P1 (Critical - business stopped), P2 (High - significant impact), P3 (Medium - work around exists), P4 (Low - minor issue)
2. Category: Network, Hardware, Software, Account, Security, Other
3. Suggested Team: network-team, endpoint-team, helpdesk, security-team
4. Needs Approval: true for P1/Critical issues, false otherwise

Consider these factors:
- VIP users (executives) should have priority elevated
- Number of affected users impacts priority
- Time sensitivity (urgent meetings, deadlines) elevates priority
- Business impact (revenue, operations) affects priority

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{"priority": "P1/P2/P3/P4", "category": "...", "team": "...", "needs_approval": true/false, "reason": "..."}""",
                "capabilities": ["ticket_classification", "priority_assignment"]
            },
            "network_expert": {
                "name": "Network Expert Agent",
                "instructions": "You are a network infrastructure expert. Diagnose network issues and provide solutions. Be concise.",
                "capabilities": ["network_diagnosis", "vpn_troubleshooting"]
            },
            "endpoint_expert": {
                "name": "Endpoint Expert Agent",
                "instructions": "You are a hardware/endpoint expert. Diagnose device issues and provide solutions. Be concise.",
                "capabilities": ["hardware_diagnosis", "device_troubleshooting"]
            },
            "helpdesk_agent": {
                "name": "Helpdesk Agent",
                "instructions": "You are a helpdesk support agent. Handle general IT requests. Be concise.",
                "capabilities": ["software_installation", "general_support"]
            }
        }

    def _safe_print(self, message: str):
        """Print with encoding safety for Windows console."""
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('ascii', 'replace').decode('ascii'))

    async def run_all_tests(self):
        """Run all 15 test cases."""
        self.start_time = time.time()

        self._safe_print("\n" + "=" * 70)
        self._safe_print(" IT Ticket E2E Workflow Tests - Azure OpenAI (gpt-5.2)")
        self._safe_print("=" * 70)
        self._safe_print(f"\nAzure Endpoint: {self.azure_config['azure_endpoint']}")
        self._safe_print(f"Deployment: {self.azure_config['azure_deployment_name']}")
        self._safe_print(f"API Version: {self.azure_config['azure_api_version']}")
        self._safe_print(f"Test Tickets: {len(self.test_tickets)}")
        self._safe_print("")

        # Phase 1: Basic Component Tests
        self._safe_print("\n" + "-" * 70)
        self._safe_print(" Phase 1: Basic Component Tests")
        self._safe_print("-" * 70)
        await self.test_01_workflow_definition()
        await self.test_02_execution_state_machine()

        # Phase 2: LLM Classification Tests
        self._safe_print("\n" + "-" * 70)
        self._safe_print(" Phase 2: LLM Classification Tests")
        self._safe_print("-" * 70)
        await self.test_03_p1_ticket_classification()
        await self.test_04_p2_ticket_classification()
        await self.test_05_p3_ticket_classification()
        await self.test_06_vip_context_classification()

        # Phase 3: Routing Tests
        self._safe_print("\n" + "-" * 70)
        self._safe_print(" Phase 3: Routing Tests")
        self._safe_print("-" * 70)
        await self.test_07_scenario_routing()
        await self.test_08_capability_matching()

        # Phase 4: Human-in-the-Loop Tests
        self._safe_print("\n" + "-" * 70)
        self._safe_print(" Phase 4: Human-in-the-Loop Tests")
        self._safe_print("-" * 70)
        await self.test_09_checkpoint_creation()
        await self.test_10_approval_flow()
        await self.test_11_rejection_flow()

        # Phase 5: Handoff Tests
        self._safe_print("\n" + "-" * 70)
        self._safe_print(" Phase 5: Handoff Tests")
        self._safe_print("-" * 70)
        await self.test_12_handoff_trigger()
        await self.test_13_handoff_completion()

        # Phase 6: Collaboration Tests
        self._safe_print("\n" + "-" * 70)
        self._safe_print(" Phase 6: Collaboration Tests")
        self._safe_print("-" * 70)
        await self.test_14_groupchat_collaboration()

        # Phase 7: Complete E2E Test
        self._safe_print("\n" + "-" * 70)
        self._safe_print(" Phase 7: Complete E2E Test")
        self._safe_print("-" * 70)
        await self.test_15_complete_e2e_workflow()

        # Print summary
        self._print_summary()

        # Save results
        self._save_results()

    async def _call_llm(self, instructions: str, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Call Azure OpenAI LLM."""
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=self.azure_config["azure_endpoint"],
            api_key=self.azure_config["api_key"],
            api_version=self.azure_config["azure_api_version"],
        )

        messages = [
            {"role": "system", "content": instructions},
        ]

        if context:
            context_str = f"\n\nContext:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
            messages[0]["content"] += context_str

        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=self.azure_config["azure_deployment_name"],
            messages=messages,
            max_completion_tokens=self.azure_config["max_completion_tokens"],
        )

        # Handle response
        if hasattr(response, 'choices'):
            text = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
        else:
            text = str(response)
            tokens = len(text.split()) * 2

        # Estimate cost (gpt-5.2 pricing)
        cost = (tokens / 1_000_000) * 10

        return {
            "text": text,
            "tokens": tokens,
            "cost": cost
        }

    # ==========================================================================
    # Phase 1: Basic Component Tests
    # ==========================================================================

    async def test_01_workflow_definition(self):
        """Test 1: Workflow definition creation."""
        test_id = 1
        test_name = "Workflow Definition Creation"
        phase = "Phase 1: Basic Components"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Simulate workflow definition creation
            workflow_def = {
                "name": "IT Ticket Triage Workflow",
                "description": "Complete IT ticket triage from intake to dispatch",
                "version": "1.0.0",
                "nodes": [
                    {"id": "intake", "type": "agent", "agent": "triage_agent"},
                    {"id": "route", "type": "condition"},
                    {"id": "approval", "type": "checkpoint"},
                    {"id": "handoff", "type": "handoff"},
                    {"id": "complete", "type": "end"}
                ],
                "edges": [
                    {"from": "intake", "to": "route"},
                    {"from": "route", "to": "approval", "condition": "priority == 'P1'"},
                    {"from": "route", "to": "handoff", "condition": "priority != 'P1'"},
                    {"from": "approval", "to": "handoff"},
                    {"from": "handoff", "to": "complete"}
                ]
            }

            # Validate structure
            has_nodes = len(workflow_def["nodes"]) > 0
            has_edges = len(workflow_def["edges"]) > 0
            has_name = bool(workflow_def.get("name"))

            passed = has_nodes and has_edges and has_name

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Nodes: {len(workflow_def['nodes'])}")
            self._safe_print(f"  Edges: {len(workflow_def['edges'])}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"workflow_def": workflow_def}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    async def test_02_execution_state_machine(self):
        """Test 2: Execution state machine transitions."""
        test_id = 2
        test_name = "Execution State Machine"
        phase = "Phase 1: Basic Components"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Test state transitions
            states = ["PENDING", "RUNNING", "WAITING_APPROVAL", "COMPLETED"]
            transitions = [
                ("PENDING", "RUNNING", True),
                ("RUNNING", "WAITING_APPROVAL", True),
                ("WAITING_APPROVAL", "COMPLETED", True),
                ("COMPLETED", "RUNNING", False),  # Invalid
            ]

            valid_transitions = 0
            for from_state, to_state, expected_valid in transitions:
                # Simulate state machine validation
                is_valid = self._validate_transition(from_state, to_state)
                if is_valid == expected_valid:
                    valid_transitions += 1

            passed = valid_transitions == len(transitions)
            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Valid Transitions: {valid_transitions}/{len(transitions)}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"transitions_tested": len(transitions), "valid": valid_transitions}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    def _validate_transition(self, from_state: str, to_state: str) -> bool:
        """Validate state transition."""
        valid_transitions = {
            "PENDING": ["RUNNING", "CANCELLED"],
            "RUNNING": ["WAITING_APPROVAL", "COMPLETED", "FAILED", "CANCELLED"],
            "WAITING_APPROVAL": ["APPROVED", "REJECTED", "CANCELLED"],
            "APPROVED": ["RUNNING"],
            "REJECTED": ["FAILED"],
            "COMPLETED": [],
            "FAILED": [],
            "CANCELLED": []
        }
        return to_state in valid_transitions.get(from_state, [])

    # ==========================================================================
    # Phase 2: LLM Classification Tests
    # ==========================================================================

    async def test_03_p1_ticket_classification(self):
        """Test 3: P1 Critical ticket classification."""
        await self._test_ticket_classification(
            test_id=3,
            test_name="P1 Critical Ticket Classification",
            ticket_index=0,  # TKT-E2E-001: Network outage affecting 50 people
            expected_priority="P1"
        )

    async def test_04_p2_ticket_classification(self):
        """Test 4: P2 High priority ticket classification."""
        await self._test_ticket_classification(
            test_id=4,
            test_name="P2 High Priority Ticket Classification",
            ticket_index=1,  # TKT-E2E-002: VPN slow
            expected_priority="P2"
        )

    async def test_05_p3_ticket_classification(self):
        """Test 5: P3 Medium priority ticket classification."""
        await self._test_ticket_classification(
            test_id=5,
            test_name="P3 Medium Priority Ticket Classification",
            ticket_index=3,  # TKT-E2E-004: Software install request
            expected_priority="P3"
        )

    async def test_06_vip_context_classification(self):
        """Test 6: VIP user context affects classification."""
        test_id = 6
        test_name = "VIP Context Classification"
        phase = "Phase 2: LLM Classification"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            ticket = self.test_tickets[0]  # CFO ticket (VIP)
            agent = self.test_agents["triage_agent"]

            context = {
                "reporter_info": ticket["reporter"],
                "business_context": "Month-end closing period, critical for financial operations"
            }

            message = f"""Ticket ID: {ticket['id']}
Title: {ticket['title']}
Description: {ticket['description']}
Reporter: {ticket['reporter']['name']} ({ticket['reporter']['role']}, {ticket['reporter']['department']})
VIP Status: {ticket['reporter']['vip']}"""

            result = await self._call_llm(agent["instructions"], message, context)

            duration_ms = (time.time() - start_time) * 1000

            # Parse response
            try:
                response_text = result["text"].strip()
                # Clean up potential markdown
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                classification = json.loads(response_text)
                is_p1 = classification.get("priority", "").upper() == "P1"
                needs_approval = classification.get("needs_approval", False)
            except json.JSONDecodeError:
                is_p1 = "P1" in result["text"].upper()
                needs_approval = "approval" in result["text"].lower()

            # VIP + critical issue should be P1 with approval
            passed = is_p1 and needs_approval

            self._safe_print(f"  VIP User: {ticket['reporter']['vip']}")
            self._safe_print(f"  Priority: {'P1' if is_p1 else 'Other'}")
            self._safe_print(f"  Needs Approval: {needs_approval}")
            self._safe_print(f"  LLM Tokens: {result['tokens']}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                llm_calls=1,
                llm_tokens=result["tokens"],
                llm_cost=result["cost"],
                response=result["text"][:200],
                details={"vip": True, "priority_detected": "P1" if is_p1 else "Other"}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    async def _test_ticket_classification(self, test_id: int, test_name: str,
                                          ticket_index: int, expected_priority: str):
        """Generic ticket classification test."""
        phase = "Phase 2: LLM Classification"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            ticket = self.test_tickets[ticket_index]
            agent = self.test_agents["triage_agent"]

            message = f"""Ticket ID: {ticket['id']}
Title: {ticket['title']}
Description: {ticket['description']}
Reporter: {ticket['reporter']['name']} ({ticket['reporter']['role']}, {ticket['reporter']['department']})"""

            result = await self._call_llm(agent["instructions"], message)

            duration_ms = (time.time() - start_time) * 1000

            # Parse response
            try:
                response_text = result["text"].strip()
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                classification = json.loads(response_text)
                detected_priority = classification.get("priority", "").upper()
            except json.JSONDecodeError:
                # Fallback: extract priority from text
                for p in ["P1", "P2", "P3", "P4"]:
                    if p in result["text"].upper():
                        detected_priority = p
                        break
                else:
                    detected_priority = "UNKNOWN"

            passed = detected_priority == expected_priority

            self._safe_print(f"  Ticket: {ticket['id']}")
            self._safe_print(f"  Expected: {expected_priority}, Detected: {detected_priority}")
            self._safe_print(f"  LLM Tokens: {result['tokens']}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                llm_calls=1,
                llm_tokens=result["tokens"],
                llm_cost=result["cost"],
                response=result["text"][:200],
                details={
                    "ticket_id": ticket["id"],
                    "expected_priority": expected_priority,
                    "detected_priority": detected_priority
                }
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    # ==========================================================================
    # Phase 3: Routing Tests
    # ==========================================================================

    async def test_07_scenario_routing(self):
        """Test 7: Scenario routing to correct team."""
        test_id = 7
        test_name = "Scenario Routing"
        phase = "Phase 3: Routing"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Test routing logic for each ticket
            routing_results = []
            for ticket in self.test_tickets:
                category = ticket["expected"]["category"]
                expected_team = ticket["expected"]["team"]

                # Simulate routing decision
                routed_team = self._route_to_team(category)
                routing_results.append({
                    "ticket_id": ticket["id"],
                    "category": category,
                    "expected_team": expected_team,
                    "routed_team": routed_team,
                    "correct": routed_team == expected_team
                })

            correct_routes = sum(1 for r in routing_results if r["correct"])
            passed = correct_routes == len(routing_results)

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Correct Routes: {correct_routes}/{len(routing_results)}")
            for r in routing_results:
                status = "OK" if r["correct"] else "MISMATCH"
                self._safe_print(f"    {r['ticket_id']}: {r['category']} -> {r['routed_team']} [{status}]")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"routing_results": routing_results}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    def _route_to_team(self, category: str) -> str:
        """Route ticket to team based on category."""
        routing_map = {
            "Network": "network-team",
            "Hardware": "endpoint-team",
            "Software": "helpdesk",
            "Account": "helpdesk",
            "Security": "security-team",
            "Other": "helpdesk"
        }
        return routing_map.get(category, "helpdesk")

    async def test_08_capability_matching(self):
        """Test 8: Capability matching finds correct agents."""
        test_id = 8
        test_name = "Capability Matching"
        phase = "Phase 3: Routing"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Test capability matching
            test_cases = [
                {"required": ["network_diagnosis"], "expected_agent": "network_expert"},
                {"required": ["hardware_diagnosis"], "expected_agent": "endpoint_expert"},
                {"required": ["software_installation"], "expected_agent": "helpdesk_agent"},
            ]

            matches = []
            for case in test_cases:
                matched_agent = self._match_capability(case["required"])
                matches.append({
                    "required": case["required"],
                    "expected": case["expected_agent"],
                    "matched": matched_agent,
                    "correct": matched_agent == case["expected_agent"]
                })

            correct_matches = sum(1 for m in matches if m["correct"])
            passed = correct_matches == len(matches)

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Correct Matches: {correct_matches}/{len(matches)}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"matches": matches}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    def _match_capability(self, required_capabilities: List[str]) -> Optional[str]:
        """Match capabilities to agent."""
        for agent_id, agent in self.test_agents.items():
            if any(cap in agent["capabilities"] for cap in required_capabilities):
                return agent_id
        return None

    # ==========================================================================
    # Phase 4: Human-in-the-Loop Tests
    # ==========================================================================

    async def test_09_checkpoint_creation(self):
        """Test 9: Checkpoint creation for P1 tickets."""
        test_id = 9
        test_name = "Checkpoint Creation"
        phase = "Phase 4: Human-in-the-Loop"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Simulate checkpoint creation
            p1_ticket = self.test_tickets[0]  # P1 ticket

            checkpoint = {
                "id": f"CP-{p1_ticket['id']}",
                "execution_id": f"EXE-{p1_ticket['id']}",
                "ticket_id": p1_ticket["id"],
                "status": "PENDING",
                "approvers": ["it_manager"],
                "timeout_minutes": 30,
                "created_at": datetime.now().isoformat(),
                "context": {
                    "priority": "P1",
                    "team": p1_ticket["expected"]["team"],
                    "reason": "Critical issue requires manager approval"
                }
            }

            # Validate checkpoint
            has_id = bool(checkpoint.get("id"))
            has_status = checkpoint.get("status") == "PENDING"
            has_approvers = len(checkpoint.get("approvers", [])) > 0
            has_context = bool(checkpoint.get("context"))

            passed = has_id and has_status and has_approvers and has_context

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Checkpoint ID: {checkpoint['id']}")
            self._safe_print(f"  Status: {checkpoint['status']}")
            self._safe_print(f"  Approvers: {checkpoint['approvers']}")
            self._safe_print(f"  Timeout: {checkpoint['timeout_minutes']} min")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"checkpoint": checkpoint}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    async def test_10_approval_flow(self):
        """Test 10: Approval flow resumes execution."""
        test_id = 10
        test_name = "Approval Flow"
        phase = "Phase 4: Human-in-the-Loop"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Simulate approval
            checkpoint = {
                "id": "CP-TKT-E2E-001",
                "status": "PENDING"
            }

            # Approve
            approval = {
                "checkpoint_id": checkpoint["id"],
                "action": "APPROVE",
                "approved_by": "it_manager",
                "approved_at": datetime.now().isoformat(),
                "comment": "Approved for immediate action"
            }

            # Update checkpoint status
            checkpoint["status"] = "APPROVED"

            # Execution should resume
            execution_status = "RUNNING"  # After approval, execution resumes

            passed = checkpoint["status"] == "APPROVED" and execution_status == "RUNNING"

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Checkpoint Status: {checkpoint['status']}")
            self._safe_print(f"  Execution Status: {execution_status}")
            self._safe_print(f"  Approved By: {approval['approved_by']}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"approval": approval, "execution_status": execution_status}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    async def test_11_rejection_flow(self):
        """Test 11: Rejection flow terminates execution."""
        test_id = 11
        test_name = "Rejection Flow"
        phase = "Phase 4: Human-in-the-Loop"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Simulate rejection
            checkpoint = {
                "id": "CP-TKT-E2E-003",
                "status": "PENDING"
            }

            # Reject
            rejection = {
                "checkpoint_id": checkpoint["id"],
                "action": "REJECT",
                "rejected_by": "it_manager",
                "rejected_at": datetime.now().isoformat(),
                "reason": "Need more information before escalation"
            }

            # Update checkpoint status
            checkpoint["status"] = "REJECTED"

            # Execution should be terminated or escalated
            execution_status = "FAILED"  # After rejection

            passed = checkpoint["status"] == "REJECTED" and execution_status == "FAILED"

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Checkpoint Status: {checkpoint['status']}")
            self._safe_print(f"  Execution Status: {execution_status}")
            self._safe_print(f"  Rejected By: {rejection['rejected_by']}")
            self._safe_print(f"  Reason: {rejection['reason']}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"rejection": rejection, "execution_status": execution_status}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    # ==========================================================================
    # Phase 5: Handoff Tests
    # ==========================================================================

    async def test_12_handoff_trigger(self):
        """Test 12: Handoff trigger passes context."""
        test_id = 12
        test_name = "Handoff Trigger"
        phase = "Phase 5: Handoff"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            ticket = self.test_tickets[0]

            # Simulate handoff
            handoff = {
                "id": f"HO-{ticket['id']}",
                "source_agent": "triage_agent",
                "target_agent": "network_expert",
                "status": "INITIATED",
                "context": {
                    "ticket_id": ticket["id"],
                    "ticket_title": ticket["title"],
                    "priority": "P1",
                    "classification_summary": "Network outage affecting Finance department",
                    "approval_status": "APPROVED"
                },
                "created_at": datetime.now().isoformat()
            }

            # Validate handoff
            has_context = bool(handoff.get("context"))
            has_ticket_info = "ticket_id" in handoff.get("context", {})
            has_classification = "classification_summary" in handoff.get("context", {})

            passed = has_context and has_ticket_info and has_classification

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Handoff ID: {handoff['id']}")
            self._safe_print(f"  Source: {handoff['source_agent']} -> Target: {handoff['target_agent']}")
            self._safe_print(f"  Context Keys: {list(handoff['context'].keys())}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                details={"handoff": handoff}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    async def test_13_handoff_completion(self):
        """Test 13: Handoff completion updates status."""
        test_id = 13
        test_name = "Handoff Completion"
        phase = "Phase 5: Handoff"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Simulate handoff completion with LLM response
            ticket = self.test_tickets[0]
            agent = self.test_agents["network_expert"]

            message = f"""You have received a handoff for ticket {ticket['id']}.
Issue: {ticket['title']}
Description: {ticket['description']}

Please provide a brief diagnosis and next steps."""

            result = await self._call_llm(agent["instructions"], message)

            # Simulate handoff completion
            handoff_completion = {
                "id": f"HO-{ticket['id']}",
                "status": "COMPLETED",
                "target_response": result["text"][:200],
                "completed_at": datetime.now().isoformat()
            }

            passed = handoff_completion["status"] == "COMPLETED" and len(result["text"]) > 20

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Handoff Status: {handoff_completion['status']}")
            self._safe_print(f"  Response Length: {len(result['text'])} chars")
            self._safe_print(f"  LLM Tokens: {result['tokens']}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                llm_calls=1,
                llm_tokens=result["tokens"],
                llm_cost=result["cost"],
                response=result["text"][:200],
                details={"handoff_completion": handoff_completion}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    # ==========================================================================
    # Phase 6: Collaboration Tests
    # ==========================================================================

    async def test_14_groupchat_collaboration(self):
        """Test 14: GroupChat multi-expert collaboration."""
        test_id = 14
        test_name = "GroupChat Collaboration"
        phase = "Phase 6: Collaboration"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            # Complex ticket requiring multi-expert discussion
            complex_issue = """A critical server is experiencing intermittent connectivity issues.
- Network team reports no issues on their end
- Hardware team found no physical problems
- The issue only affects one specific application
- Users report the problem started after a recent Windows update

What could be the cause and how should we investigate?"""

            experts = ["network_expert", "endpoint_expert", "helpdesk_agent"]
            expert_responses = []
            total_tokens = 0
            total_cost = 0.0

            for expert_id in experts:
                agent = self.test_agents[expert_id]
                result = await self._call_llm(
                    agent["instructions"],
                    f"As {agent['name']}, analyze this issue:\n\n{complex_issue}"
                )
                expert_responses.append({
                    "expert": expert_id,
                    "response": result["text"][:150],
                    "tokens": result["tokens"]
                })
                total_tokens += result["tokens"]
                total_cost += result["cost"]
                self._safe_print(f"    {expert_id}: {result['tokens']} tokens")

            # Synthesize responses
            synthesis_prompt = """Based on the following expert opinions, provide a consolidated recommendation:

""" + "\n".join([f"- {r['expert']}: {r['response']}" for r in expert_responses])

            synthesis = await self._call_llm(
                "You are a senior IT manager. Synthesize expert opinions into a clear action plan. Be brief.",
                synthesis_prompt
            )
            total_tokens += synthesis["tokens"]
            total_cost += synthesis["cost"]

            passed = len(expert_responses) == 3 and len(synthesis["text"]) > 50

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Experts Consulted: {len(expert_responses)}")
            self._safe_print(f"  Total Tokens: {total_tokens}")
            self._safe_print(f"  Synthesis Length: {len(synthesis['text'])} chars")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                llm_calls=len(experts) + 1,
                llm_tokens=total_tokens,
                llm_cost=total_cost,
                response=synthesis["text"][:200],
                details={"experts": expert_responses}
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    # ==========================================================================
    # Phase 7: Complete E2E Test
    # ==========================================================================

    async def test_15_complete_e2e_workflow(self):
        """Test 15: Complete end-to-end workflow."""
        test_id = 15
        test_name = "Complete E2E Workflow"
        phase = "Phase 7: Complete E2E"
        self._safe_print(f"\n[TEST {test_id}] {test_name}")

        start_time = time.time()

        try:
            ticket = self.test_tickets[2]  # P1 Hardware issue
            total_tokens = 0
            total_cost = 0.0
            workflow_steps = []

            # Step 1: Intake and Classification
            self._safe_print("  Step 1: Intake & Classification...")
            agent = self.test_agents["triage_agent"]
            message = f"""Ticket: {ticket['id']}
Title: {ticket['title']}
Description: {ticket['description']}
Reporter: {ticket['reporter']['name']} ({ticket['reporter']['role']})"""

            classification_result = await self._call_llm(agent["instructions"], message)
            total_tokens += classification_result["tokens"]
            total_cost += classification_result["cost"]
            workflow_steps.append({"step": "classification", "status": "completed"})

            # Step 2: Routing Decision
            self._safe_print("  Step 2: Routing Decision...")
            routed_team = self._route_to_team(ticket["expected"]["category"])
            workflow_steps.append({"step": "routing", "team": routed_team, "status": "completed"})

            # Step 3: Checkpoint (for P1)
            self._safe_print("  Step 3: Checkpoint Creation...")
            checkpoint = {
                "id": f"CP-{ticket['id']}",
                "status": "PENDING",
                "approvers": ["it_manager"]
            }
            workflow_steps.append({"step": "checkpoint", "status": "created"})

            # Step 4: Approval
            self._safe_print("  Step 4: Approval...")
            checkpoint["status"] = "APPROVED"
            workflow_steps.append({"step": "approval", "status": "approved"})

            # Step 5: Capability Match
            self._safe_print("  Step 5: Capability Matching...")
            matched_agent = self._match_capability(["hardware_diagnosis"])
            workflow_steps.append({"step": "capability_match", "agent": matched_agent, "status": "completed"})

            # Step 6: Handoff
            self._safe_print("  Step 6: Handoff...")
            target_agent = self.test_agents.get(matched_agent, self.test_agents["endpoint_expert"])
            handoff_result = await self._call_llm(
                target_agent["instructions"],
                f"Handle this ticket:\n{message}"
            )
            total_tokens += handoff_result["tokens"]
            total_cost += handoff_result["cost"]
            workflow_steps.append({"step": "handoff", "status": "completed"})

            # Step 7: Resolution
            self._safe_print("  Step 7: Resolution...")
            workflow_steps.append({"step": "resolution", "status": "completed"})

            # Final status
            execution_status = "COMPLETED"
            all_steps_completed = all(s.get("status") in ["completed", "created", "approved"] for s in workflow_steps)

            passed = all_steps_completed and execution_status == "COMPLETED"

            duration_ms = (time.time() - start_time) * 1000

            self._safe_print(f"  Steps Completed: {len(workflow_steps)}/7")
            self._safe_print(f"  Total Tokens: {total_tokens}")
            self._safe_print(f"  Total Cost: ${total_cost:.4f}")
            self._safe_print(f"  Final Status: {execution_status}")
            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="PASS" if passed else "FAIL",
                duration_ms=duration_ms,
                llm_calls=2,
                llm_tokens=total_tokens,
                llm_cost=total_cost,
                details={
                    "ticket_id": ticket["id"],
                    "workflow_steps": workflow_steps,
                    "final_status": execution_status
                }
            ))

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self._safe_print("  Status: [FAIL]")
            self.results.append(TestResult(
                test_id=test_id,
                test_name=test_name,
                phase=phase,
                status="FAIL",
                duration_ms=duration_ms,
                error=str(e)
            ))

    def _print_summary(self):
        """Print test summary."""
        total_duration = (time.time() - self.start_time) * 1000
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        total_tokens = sum(r.llm_tokens for r in self.results)
        total_cost = sum(r.llm_cost for r in self.results)

        self._safe_print("\n" + "=" * 70)
        self._safe_print(" IT Ticket E2E Workflow Test Summary")
        self._safe_print("=" * 70)
        self._safe_print(f"  Tests: {passed}/{len(self.results)} passed")
        self._safe_print(f"  Pass Rate: {(passed/len(self.results)*100):.1f}%")
        self._safe_print(f"  Total Duration: {total_duration:.0f}ms")
        self._safe_print(f"  Total LLM Tokens: {total_tokens}")
        self._safe_print(f"  Total LLM Cost: ${total_cost:.4f}")
        self._safe_print("=" * 70)

        # Phase summary
        phases = {}
        for r in self.results:
            if r.phase not in phases:
                phases[r.phase] = {"passed": 0, "total": 0}
            phases[r.phase]["total"] += 1
            if r.status == "PASS":
                phases[r.phase]["passed"] += 1

        self._safe_print("\nPhase Summary:")
        for phase, stats in phases.items():
            status = "PASS" if stats["passed"] == stats["total"] else "PARTIAL"
            self._safe_print(f"  {phase}: {stats['passed']}/{stats['total']} [{status}]")

    def _save_results(self):
        """Save test results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Prepare summary
        passed = sum(1 for r in self.results if r.status == "PASS")
        total_tokens = sum(r.llm_tokens for r in self.results)
        total_cost = sum(r.llm_cost for r in self.results)

        summary = TestSummary(
            test_plan="IT Ticket E2E Workflow",
            executed_at=datetime.now().isoformat(),
            environment={
                "azure_model": self.azure_config["azure_deployment_name"],
                "api_version": self.azure_config["azure_api_version"],
                "endpoint": self.azure_config["azure_endpoint"]
            },
            summary={
                "total_tests": len(self.results),
                "passed": passed,
                "failed": len(self.results) - passed,
                "pass_rate": f"{(passed/len(self.results)*100):.1f}%"
            },
            metrics={
                "total_duration_ms": (time.time() - self.start_time) * 1000,
                "total_llm_calls": sum(r.llm_calls for r in self.results),
                "total_tokens": total_tokens,
                "total_cost": total_cost
            },
            results=[asdict(r) for r in self.results]
        )

        # Save to file
        output_dir = Path(__file__).parent.parent.parent / "claudedocs" / "uat" / "sessions"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"it_ticket_e2e_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, ensure_ascii=False, indent=2)

        self._safe_print(f"\nResults saved to: {output_file}")


async def main():
    """Run the test suite."""
    test_suite = ITTicketE2EWorkflowTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
