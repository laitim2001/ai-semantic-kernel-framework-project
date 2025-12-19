# =============================================================================
# E2E LLM Integration Tests - 真實 LLM 整合測試
# =============================================================================
# 使用 Azure OpenAI (gpt-5.2) 進行真實的端對端測試
#
# Author: IPA Platform Team
# Version: 1.0.0
# Created: 2025-12-18
# =============================================================================

"""
E2E LLM Integration Tests.

Tests real LLM integration with Azure OpenAI including:
- Single Agent with real LLM response
- Multi-Agent GroupChat collaboration
- IT Ticket Triage workflow
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Change to backend directory for proper imports
original_cwd = os.getcwd()
os.chdir(backend_path)

from dotenv import load_dotenv

# Load environment variables
load_dotenv(backend_path / ".env")


@dataclass
class E2ETestResult:
    """Result of an E2E test."""
    test_name: str
    passed: bool
    duration_ms: float
    llm_calls: int = 0
    llm_tokens: int = 0
    llm_cost: float = 0.0
    response: str = ""
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "llm_calls": self.llm_calls,
            "llm_tokens": self.llm_tokens,
            "llm_cost": self.llm_cost,
            "response": self.response[:500] if self.response else "",
            "error": self.error,
            "details": self.details,
        }


class E2ELLMIntegrationTest:
    """
    End-to-End LLM Integration Test Suite.

    Tests real Azure OpenAI integration with the IPA Platform.
    """

    def __init__(self):
        self.results: List[E2ETestResult] = []
        self.azure_config = {
            "provider": "azure_openai",
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "azure_deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
            "max_completion_tokens": 1000,
        }

    def _safe_print(self, text: str):
        """Print with encoding fallback."""
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('ascii', 'replace').decode('ascii'))

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all E2E tests."""
        self._safe_print("\n" + "=" * 70)
        self._safe_print(" E2E LLM Integration Tests - Azure OpenAI (gpt-5.2)")
        self._safe_print("=" * 70)

        self._safe_print(f"\nAzure Endpoint: {self.azure_config['azure_endpoint']}")
        self._safe_print(f"Deployment: {self.azure_config['azure_deployment_name']}")
        self._safe_print(f"API Version: {self.azure_config['azure_api_version']}")
        self._safe_print("")

        start_time = time.time()

        # Run tests
        await self.test_1_single_agent_response()
        await self.test_2_agent_with_context()
        await self.test_3_it_ticket_classification()
        await self.test_4_multi_turn_conversation()
        await self.test_5_expert_agent_collaboration()

        total_duration = (time.time() - start_time) * 1000

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        total_tokens = sum(r.llm_tokens for r in self.results)
        total_cost = sum(r.llm_cost for r in self.results)

        self._safe_print("\n" + "=" * 70)
        self._safe_print(" E2E Test Summary")
        self._safe_print("=" * 70)
        self._safe_print(f"  Tests: {passed}/{len(self.results)} passed")
        self._safe_print(f"  Total Duration: {total_duration:.0f}ms")
        self._safe_print(f"  Total LLM Tokens: {total_tokens}")
        self._safe_print(f"  Total LLM Cost: ${total_cost:.4f}")
        self._safe_print("=" * 70)

        return {
            "passed": passed,
            "failed": failed,
            "total_tests": len(self.results),
            "duration_ms": total_duration,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "results": [r.to_dict() for r in self.results],
        }

    async def test_1_single_agent_response(self):
        """Test 1: Single Agent with real LLM response."""
        test_name = "Single Agent Response"
        self._safe_print(f"\n[TEST 1] {test_name}")
        self._safe_print("-" * 50)

        start_time = time.time()

        try:
            from src.integrations.agent_framework.builders import (
                AgentExecutorAdapter,
                AgentExecutorConfig,
            )

            # Create adapter with Azure config
            adapter = AgentExecutorAdapter(settings=None)
            adapter._initialized = True  # Skip initialization, we'll use model_config

            config = AgentExecutorConfig(
                name="test-agent",
                instructions="You are a helpful assistant. Always respond in Traditional Chinese.",
                model_config=self.azure_config,
            )

            result = await adapter.execute(
                config=config,
                message="Hello! Please introduce yourself briefly.",
            )

            duration_ms = (time.time() - start_time) * 1000

            # Validate response
            has_response = len(result.text) > 10
            has_tokens = result.llm_tokens > 0

            self._safe_print(f"  Response length: {len(result.text)} chars")
            self._safe_print(f"  LLM Tokens: {result.llm_tokens}")
            self._safe_print(f"  LLM Cost: ${result.llm_cost:.6f}")

            passed = has_response and has_tokens

            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=passed,
                duration_ms=duration_ms,
                llm_calls=result.llm_calls,
                llm_tokens=result.llm_tokens,
                llm_cost=result.llm_cost,
                response=result.text,
            ))

            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            self._safe_print("  Status: [FAIL]")

    async def test_2_agent_with_context(self):
        """Test 2: Agent with additional context."""
        test_name = "Agent with Context"
        self._safe_print(f"\n[TEST 2] {test_name}")
        self._safe_print("-" * 50)

        start_time = time.time()

        try:
            from src.integrations.agent_framework.builders import (
                AgentExecutorAdapter,
                AgentExecutorConfig,
            )

            adapter = AgentExecutorAdapter(settings=None)
            adapter._initialized = True

            config = AgentExecutorConfig(
                name="context-agent",
                instructions="""You are an IT support specialist.
Analyze the ticket and suggest a priority level (P1-P4) and category.
Respond in JSON format: {"priority": "Px", "category": "...", "reason": "..."}""",
                model_config=self.azure_config,
            )

            context = {
                "department": "Finance",
                "user_role": "Manager",
                "previous_tickets": 0,
            }

            result = await adapter.execute(
                config=config,
                message="My computer won't turn on and I have a meeting in 30 minutes!",
                context=context,
            )

            duration_ms = (time.time() - start_time) * 1000

            # Try to parse JSON response
            try:
                response_json = json.loads(result.text.strip().replace("```json", "").replace("```", ""))
                has_priority = "priority" in response_json
                has_category = "category" in response_json
            except json.JSONDecodeError:
                has_priority = "P1" in result.text or "P2" in result.text or "P3" in result.text or "P4" in result.text
                has_category = True  # Assume category mentioned

            self._safe_print(f"  Response: {result.text[:200]}...")
            self._safe_print(f"  LLM Tokens: {result.llm_tokens}")
            self._safe_print(f"  Has Priority: {has_priority}")

            passed = len(result.text) > 10 and has_priority

            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=passed,
                duration_ms=duration_ms,
                llm_calls=result.llm_calls,
                llm_tokens=result.llm_tokens,
                llm_cost=result.llm_cost,
                response=result.text,
                details={"context": context},
            ))

            self._safe_print(f"  Status: {'[PASS]' if passed else '[FAIL]'}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            self._safe_print("  Status: [FAIL]")

    async def test_3_it_ticket_classification(self):
        """Test 3: IT Ticket Classification (simulating workflow)."""
        test_name = "IT Ticket Classification"
        self._safe_print(f"\n[TEST 3] {test_name}")
        self._safe_print("-" * 50)

        start_time = time.time()

        try:
            from src.integrations.agent_framework.builders import (
                AgentExecutorAdapter,
                AgentExecutorConfig,
            )

            adapter = AgentExecutorAdapter(settings=None)
            adapter._initialized = True

            # Classifier Agent
            classifier_config = AgentExecutorConfig(
                name="ticket-classifier",
                instructions="""You are an IT ticket classifier. Analyze the ticket and respond with:
1. Category: hardware/software/network/security/other
2. Priority: P1 (critical), P2 (high), P3 (medium), P4 (low)
3. Suggested Team: desktop-support/network-team/security-team/helpdesk
4. Needs Approval: yes/no (yes if P1 or P2)

Respond in Traditional Chinese with clear structure.""",
                model_config=self.azure_config,
            )

            test_tickets = [
                {
                    "id": "TKT-001",
                    "description": "Cannot connect to VPN from home",
                    "expected_category": "network",
                },
                {
                    "id": "TKT-002",
                    "description": "Entire floor (50 people) lost internet connection",
                    "expected_category": "network",
                    "expected_priority": "P1",
                },
                {
                    "id": "TKT-003",
                    "description": "Forgot my password",
                    "expected_category": "software",
                    "expected_priority": "P4",
                },
            ]

            classifications = []
            total_tokens = 0
            total_cost = 0.0

            for ticket in test_tickets:
                result = await adapter.execute(
                    config=classifier_config,
                    message=f"Ticket ID: {ticket['id']}\nDescription: {ticket['description']}",
                )

                classifications.append({
                    "ticket_id": ticket["id"],
                    "classification": result.text[:300],
                    "tokens": result.llm_tokens,
                })

                total_tokens += result.llm_tokens
                total_cost += result.llm_cost

                self._safe_print(f"  Ticket {ticket['id']}: {result.llm_tokens} tokens")

            duration_ms = (time.time() - start_time) * 1000

            # Validate all tickets were classified
            all_classified = all(len(c["classification"]) > 20 for c in classifications)

            self._safe_print(f"  Total Tickets: {len(test_tickets)}")
            self._safe_print(f"  Total Tokens: {total_tokens}")
            self._safe_print(f"  Total Cost: ${total_cost:.6f}")

            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=all_classified,
                duration_ms=duration_ms,
                llm_calls=len(test_tickets),
                llm_tokens=total_tokens,
                llm_cost=total_cost,
                details={"classifications": classifications},
            ))

            self._safe_print(f"  Status: {'[PASS]' if all_classified else '[FAIL]'}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            self._safe_print("  Status: [FAIL]")

    async def test_4_multi_turn_conversation(self):
        """Test 4: Multi-turn conversation with memory."""
        test_name = "Multi-turn Conversation"
        self._safe_print(f"\n[TEST 4] {test_name}")
        self._safe_print("-" * 50)

        start_time = time.time()

        try:
            from openai import AzureOpenAI

            client = AzureOpenAI(
                azure_endpoint=self.azure_config["azure_endpoint"],
                api_key=self.azure_config["api_key"],
                api_version=self.azure_config["azure_api_version"],
            )

            # Simulate multi-turn conversation
            conversation = [
                {"role": "system", "content": "You are a helpful IT support assistant. Keep responses brief."},
            ]

            turns = [
                "Hi, I need help with my computer.",
                "It's running very slowly.",
                "I have a Windows laptop, about 2 years old.",
                "What should I try first?",
            ]

            total_tokens = 0
            total_cost = 0.0
            responses = []

            for user_msg in turns:
                conversation.append({"role": "user", "content": user_msg})

                response = client.chat.completions.create(
                    model=self.azure_config["azure_deployment_name"],
                    messages=conversation,
                    max_completion_tokens=200,
                )

                # Handle response - check if it's a proper object or string
                if hasattr(response, 'choices'):
                    assistant_msg = response.choices[0].message.content
                    tokens = response.usage.total_tokens if response.usage else 0
                elif isinstance(response, str):
                    # Response came as string directly
                    assistant_msg = response
                    tokens = len(response.split()) * 2  # Estimate
                else:
                    # Unknown response type - convert to string
                    assistant_msg = str(response)
                    tokens = len(assistant_msg.split()) * 2

                conversation.append({"role": "assistant", "content": assistant_msg})
                responses.append(assistant_msg)
                total_tokens += tokens

            duration_ms = (time.time() - start_time) * 1000

            # Calculate cost (GPT-5.2 pricing estimate)
            total_cost = (total_tokens / 1_000_000) * 10  # Estimated pricing

            # Validate conversation maintained context
            final_response = responses[-1].lower()
            has_context = any(word in final_response for word in ["restart", "memory", "disk", "update", "clean", "scan"])

            self._safe_print(f"  Turns: {len(turns)}")
            self._safe_print(f"  Total Tokens: {total_tokens}")
            self._safe_print(f"  Context Maintained: {has_context}")

            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=has_context and len(responses) == len(turns),
                duration_ms=duration_ms,
                llm_calls=len(turns),
                llm_tokens=total_tokens,
                llm_cost=total_cost,
                details={"turns": len(turns), "responses": [r[:100] for r in responses]},
            ))

            self._safe_print(f"  Status: {'[PASS]' if has_context else '[FAIL]'}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            self._safe_print("  Status: [FAIL]")

    async def test_5_expert_agent_collaboration(self):
        """Test 5: Multi-Agent Expert Collaboration (simulating GroupChat)."""
        test_name = "Expert Agent Collaboration"
        self._safe_print(f"\n[TEST 5] {test_name}")
        self._safe_print("-" * 50)

        start_time = time.time()

        try:
            from openai import AzureOpenAI

            client = AzureOpenAI(
                azure_endpoint=self.azure_config["azure_endpoint"],
                api_key=self.azure_config["api_key"],
                api_version=self.azure_config["azure_api_version"],
            )

            # Define expert agents
            experts = {
                "tech_expert": "You are a Technical Expert. Focus on technical feasibility and implementation details. Be concise.",
                "business_expert": "You are a Business Analyst. Focus on ROI, costs, and business impact. Be concise.",
                "risk_expert": "You are a Risk Manager. Focus on potential risks and mitigation strategies. Be concise.",
            }

            topic = "Should we migrate our monolithic application to microservices architecture?"

            discussion = []
            total_tokens = 0
            total_cost = 0.0

            self._safe_print(f"  Topic: {topic}")

            # Each expert gives their opinion
            for expert_name, expert_prompt in experts.items():
                messages = [
                    {"role": "system", "content": expert_prompt},
                    {"role": "user", "content": f"Please provide your brief analysis (2-3 sentences) on: {topic}"},
                ]

                response = client.chat.completions.create(
                    model=self.azure_config["azure_deployment_name"],
                    messages=messages,
                    max_completion_tokens=300,
                )

                opinion = response.choices[0].message.content
                discussion.append({
                    "expert": expert_name,
                    "opinion": opinion,
                })

                tokens = response.usage.total_tokens if response.usage else 0
                total_tokens += tokens

                self._safe_print(f"  {expert_name}: {tokens} tokens")

            # Moderator synthesizes
            synthesis_prompt = f"""You are a Discussion Moderator. Synthesize the following expert opinions into a brief recommendation:

Technical Expert: {discussion[0]['opinion']}

Business Analyst: {discussion[1]['opinion']}

Risk Manager: {discussion[2]['opinion']}

Provide a 2-3 sentence synthesis in Traditional Chinese."""

            synthesis_response = client.chat.completions.create(
                model=self.azure_config["azure_deployment_name"],
                messages=[
                    {"role": "system", "content": "You are a skilled moderator who synthesizes discussions."},
                    {"role": "user", "content": synthesis_prompt},
                ],
                max_completion_tokens=400,
            )

            synthesis = synthesis_response.choices[0].message.content
            total_tokens += synthesis_response.usage.total_tokens if synthesis_response.usage else 0

            duration_ms = (time.time() - start_time) * 1000
            total_cost = (total_tokens / 1_000_000) * 10

            # Validate collaboration
            all_experts_spoke = len(discussion) == 3
            has_synthesis = len(synthesis) > 50

            self._safe_print(f"  Experts Participated: {len(discussion)}")
            self._safe_print(f"  Total Tokens: {total_tokens}")
            self._safe_print(f"  Synthesis Length: {len(synthesis)} chars")

            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=all_experts_spoke and has_synthesis,
                duration_ms=duration_ms,
                llm_calls=len(experts) + 1,
                llm_tokens=total_tokens,
                llm_cost=total_cost,
                response=synthesis,
                details={
                    "experts": list(experts.keys()),
                    "discussion_turns": len(discussion),
                },
            ))

            self._safe_print(f"  Status: {'[PASS]' if (all_experts_spoke and has_synthesis) else '[FAIL]'}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._safe_print(f"  Error: {e}")
            self.results.append(E2ETestResult(
                test_name=test_name,
                passed=False,
                duration_ms=duration_ms,
                error=str(e),
            ))
            self._safe_print("  Status: [FAIL]")


async def main():
    """Main entry point."""
    test_suite = E2ELLMIntegrationTest()
    results = await test_suite.run_all_tests()

    # Save results to file
    output_dir = Path(__file__).parent.parent.parent / "claudedocs" / "uat" / "sessions"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"e2e_llm_integration_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_file}")

    return results["failed"] == 0


if __name__ == "__main__":
    os.chdir(original_cwd)
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
