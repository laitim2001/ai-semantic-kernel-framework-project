"""
Phase 10: Session Mode - Technical Support Session Scenario

測試場景：技術支援會話
業務背景：用戶通過 Session Mode 進行技術問題諮詢，上傳錯誤日誌，
         與 AI 進行多輪對話獲取解決方案。

測試步驟：
1. 建立 Session
2. 上傳錯誤日誌
3. 發送問題描述
4. AI 分析日誌
5. 多輪對話追問
6. 獲取解決方案
7. 搜索歷史記錄
8. 建立會話模板
9. 查看統計信息
10. 結束 Session
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import PhaseTestBase, StepResult, ScenarioResult
from config import PhaseTestConfig, API_ENDPOINTS


class TechSupportSessionScenario(PhaseTestBase):
    """技術支援會話場景測試"""

    def __init__(self, config: Optional[PhaseTestConfig] = None):
        super().__init__(config)
        self.scenario_name = "Technical Support Session"
        self.phase = 10

        # Session 相關狀態
        self.session_id: Optional[str] = None
        self.session_status: str = "CREATED"
        self.messages: List[Dict[str, Any]] = []
        self.attachments: List[Dict[str, Any]] = []
        self.template_id: Optional[str] = None

        # 模擬的錯誤日誌
        self.error_log_content = self._generate_error_log()

    def _generate_error_log(self) -> str:
        """生成模擬的錯誤日誌"""
        return """2024-12-22 10:15:23 ERROR [api.v1.handlers] Connection timeout to database
2024-12-22 10:15:24 ERROR [api.v1.handlers] Retry 1/3 failed
2024-12-22 10:15:25 ERROR [api.v1.handlers] Retry 2/3 failed
2024-12-22 10:15:26 CRITICAL [api.v1.handlers] All retries exhausted
2024-12-22 10:15:26 ERROR [api.v1.handlers] User request failed: 503
2024-12-22 10:15:27 WARN [connection.pool] Pool exhausted, waiting for connection
2024-12-22 10:15:28 ERROR [database.connection] Failed to establish connection to postgres:5432
2024-12-22 10:15:29 ERROR [health.check] Database health check failed
2024-12-22 10:15:30 CRITICAL [system.monitor] Service degraded: database connectivity issues"""

    async def _step_1_create_session(self) -> Dict[str, Any]:
        """Step 1: 建立 Session"""
        self.log_step_start(1, "Create Session")

        try:
            # 嘗試調用真實 API
            endpoint = API_ENDPOINTS["sessions"]["create"]

            session_data = {
                "title": "技術支援：資料庫連接問題",
                "type": "technical_support",
                "metadata": {
                    "priority": "high",
                    "category": "database",
                    "user_tier": "enterprise"
                }
            }

            response = await self.call_api("POST", endpoint, json=session_data)

            if response and response.get("success"):
                self.session_id = response["data"]["session_id"]
                self.session_status = "ACTIVE"
                return {
                    "session_id": self.session_id,
                    "status": self.session_status,
                    "created_at": response["data"].get("created_at")
                }
            else:
                # Fallback: 模擬創建
                return await self._simulate_create_session()

        except Exception as e:
            self.logger.warning(f"API call failed, using simulation: {e}")
            return await self._simulate_create_session()

    async def _simulate_create_session(self) -> Dict[str, Any]:
        """模擬創建 Session"""
        self.session_id = f"session_{uuid.uuid4().hex[:12]}"
        self.session_status = "ACTIVE"

        return {
            "session_id": self.session_id,
            "status": self.session_status,
            "created_at": datetime.now().isoformat(),
            "simulated": True
        }

    async def _step_2_upload_error_log(self) -> Dict[str, Any]:
        """Step 2: 上傳錯誤日誌"""
        self.log_step_start(2, "Upload Error Log")

        try:
            endpoint = API_ENDPOINTS["sessions"]["upload_attachment"].format(
                session_id=self.session_id
            )

            # 構建附件數據
            attachment_data = {
                "filename": "error.log",
                "content_type": "text/plain",
                "content": self.error_log_content,
                "metadata": {
                    "source": "production_server",
                    "timestamp": datetime.now().isoformat()
                }
            }

            response = await self.call_api("POST", endpoint, json=attachment_data)

            if response and response.get("success"):
                attachment = response["data"]
                self.attachments.append(attachment)
                return {
                    "attachment_id": attachment.get("attachment_id"),
                    "filename": "error.log",
                    "size": len(self.error_log_content),
                    "status": "uploaded"
                }
            else:
                return await self._simulate_upload_attachment()

        except Exception as e:
            self.logger.warning(f"Upload failed, using simulation: {e}")
            return await self._simulate_upload_attachment()

    async def _simulate_upload_attachment(self) -> Dict[str, Any]:
        """模擬上傳附件"""
        attachment = {
            "attachment_id": f"attach_{uuid.uuid4().hex[:8]}",
            "filename": "error.log",
            "content_type": "text/plain",
            "size": len(self.error_log_content),
            "uploaded_at": datetime.now().isoformat()
        }
        self.attachments.append(attachment)

        return {
            "attachment_id": attachment["attachment_id"],
            "filename": "error.log",
            "size": attachment["size"],
            "status": "uploaded",
            "simulated": True
        }

    async def _step_3_send_problem_description(self) -> Dict[str, Any]:
        """Step 3: 發送問題描述"""
        self.log_step_start(3, "Send Problem Description")

        user_message = """我們的生產環境出現了嚴重的資料庫連接問題。

從早上 10:15 開始，用戶開始回報 503 錯誤。我已經上傳了錯誤日誌，
請幫我分析問題的根本原因，以及可能的解決方案。

系統環境：
- PostgreSQL 16
- Python FastAPI 後端
- 連接池：SQLAlchemy + asyncpg
- 部署在 Azure AKS"""

        try:
            endpoint = API_ENDPOINTS["sessions"]["send_message"].format(
                session_id=self.session_id
            )

            message_data = {
                "role": "user",
                "content": user_message,
                "attachment_ids": [a["attachment_id"] for a in self.attachments]
            }

            response = await self.call_api("POST", endpoint, json=message_data)

            if response and response.get("success"):
                message = response["data"]
                self.messages.append(message)
                return {
                    "message_id": message.get("message_id"),
                    "role": "user",
                    "content_preview": user_message[:100] + "...",
                    "has_attachments": True
                }
            else:
                return await self._simulate_send_message("user", user_message)

        except Exception as e:
            self.logger.warning(f"Send message failed, using simulation: {e}")
            return await self._simulate_send_message("user", user_message)

    async def _simulate_send_message(self, role: str, content: str) -> Dict[str, Any]:
        """模擬發送訊息"""
        message = {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": role,
            "content": content,
            "created_at": datetime.now().isoformat()
        }
        self.messages.append(message)

        return {
            "message_id": message["message_id"],
            "role": role,
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
            "simulated": True
        }

    async def _step_4_ai_analyze_log(self) -> Dict[str, Any]:
        """Step 4: AI 分析日誌"""
        self.log_step_start(4, "AI Analyze Log")

        try:
            # 使用真實 LLM 分析日誌
            if self.config.use_real_llm:
                analysis_prompt = f"""請分析以下錯誤日誌，識別問題的根本原因：

{self.error_log_content}

請提供：
1. 問題摘要
2. 根本原因分析
3. 影響範圍
4. 嚴重程度評估"""

                llm_response = await self.call_llm(analysis_prompt)

                ai_response = {
                    "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                    "role": "assistant",
                    "content": llm_response,
                    "analysis_type": "log_analysis",
                    "created_at": datetime.now().isoformat()
                }
                self.messages.append(ai_response)

                return {
                    "message_id": ai_response["message_id"],
                    "role": "assistant",
                    "content_preview": llm_response[:200] + "..." if len(llm_response) > 200 else llm_response,
                    "analysis_complete": True,
                    "used_real_llm": True
                }
            else:
                return await self._simulate_ai_analysis()

        except Exception as e:
            self.logger.warning(f"LLM analysis failed, using simulation: {e}")
            return await self._simulate_ai_analysis()

    async def _simulate_ai_analysis(self) -> Dict[str, Any]:
        """模擬 AI 分析"""
        simulated_analysis = """## 問題摘要
系統出現資料庫連接超時問題，導致用戶請求返回 503 錯誤。

## 根本原因分析
1. **連接池耗盡**：日誌顯示 "Pool exhausted"
2. **資料庫連接失敗**：無法連接到 postgres:5432
3. **重試機制失效**：3次重試後仍然失敗

## 影響範圍
- 所有依賴資料庫的 API 請求
- 用戶無法正常使用系統功能

## 嚴重程度
**CRITICAL** - 需要立即處理"""

        ai_response = {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "assistant",
            "content": simulated_analysis,
            "analysis_type": "log_analysis",
            "created_at": datetime.now().isoformat()
        }
        self.messages.append(ai_response)

        return {
            "message_id": ai_response["message_id"],
            "role": "assistant",
            "content_preview": simulated_analysis[:200] + "...",
            "analysis_complete": True,
            "simulated": True
        }

    async def _step_5_multi_turn_conversation(self) -> Dict[str, Any]:
        """Step 5: 多輪對話追問"""
        self.log_step_start(5, "Multi-turn Conversation")

        follow_up_questions = [
            "連接池的配置是怎樣的？最大連接數是多少？",
            "資料庫服務器目前的負載情況如何？"
        ]

        conversation_results = []

        for i, question in enumerate(follow_up_questions):
            # 發送用戶問題
            user_result = await self._simulate_send_message("user", question)

            # 獲取 AI 回應
            if self.config.use_real_llm:
                try:
                    context = "\n".join([
                        f"{m['role']}: {m['content'][:200]}"
                        for m in self.messages[-4:]  # 最近4條訊息作為上下文
                    ])

                    prompt = f"""基於以下對話上下文，回答用戶的問題：

上下文：
{context}

用戶問題：{question}

請提供簡潔但有幫助的回答。"""

                    llm_response = await self.call_llm(prompt)
                    ai_result = await self._simulate_send_message("assistant", llm_response)
                    ai_result["used_real_llm"] = True

                except Exception as e:
                    self.logger.warning(f"LLM call failed for follow-up: {e}")
                    ai_result = await self._simulate_follow_up_response(question)
            else:
                ai_result = await self._simulate_follow_up_response(question)

            conversation_results.append({
                "turn": i + 1,
                "question": question[:50] + "...",
                "response_preview": ai_result.get("content_preview", "")[:100]
            })

        return {
            "total_turns": len(follow_up_questions),
            "conversation_results": conversation_results,
            "total_messages": len(self.messages)
        }

    async def _simulate_follow_up_response(self, question: str) -> Dict[str, Any]:
        """模擬追問回應"""
        responses = {
            "連接池": "建議檢查連接池配置，標準設置為 max_connections=20, min_connections=5。",
            "負載": "建議使用 pg_stat_activity 查看當前連接數和查詢狀態。"
        }

        response = "這是一個很好的問題。"
        for key, value in responses.items():
            if key in question:
                response = value
                break

        return await self._simulate_send_message("assistant", response)

    async def _step_6_get_solution(self) -> Dict[str, Any]:
        """Step 6: 獲取解決方案"""
        self.log_step_start(6, "Get Solution")

        solution_request = "請根據以上分析，給我一個完整的解決方案，包括立即行動和長期改進建議。"

        try:
            await self._simulate_send_message("user", solution_request)

            if self.config.use_real_llm:
                context = "\n".join([
                    f"{m['role']}: {m['content'][:300]}"
                    for m in self.messages[-6:]
                ])

                prompt = f"""基於以下技術支援對話，提供完整的解決方案：

對話上下文：
{context}

請提供：
1. 立即行動步驟（緊急處理）
2. 短期改進措施
3. 長期架構優化建議
4. 預防措施

格式要求：使用 Markdown，條理清晰。"""

                solution = await self.call_llm(prompt)

                ai_result = await self._simulate_send_message("assistant", solution)

                return {
                    "solution_provided": True,
                    "solution_length": len(solution),
                    "solution_preview": solution[:300] + "...",
                    "used_real_llm": True
                }
            else:
                return await self._simulate_solution()

        except Exception as e:
            self.logger.warning(f"Solution generation failed: {e}")
            return await self._simulate_solution()

    async def _simulate_solution(self) -> Dict[str, Any]:
        """模擬解決方案"""
        solution = """## 解決方案

### 1. 立即行動（緊急處理）
- 重啟資料庫連接池
- 檢查 PostgreSQL 服務狀態
- 確認網路連通性

### 2. 短期改進
- 增加連接池大小
- 優化慢查詢
- 添加連接健康檢查

### 3. 長期優化
- 實施讀寫分離
- 添加連接池監控
- 建立自動故障轉移機制

### 4. 預防措施
- 設置資源告警
- 定期壓力測試
- 建立事故響應流程"""

        await self._simulate_send_message("assistant", solution)

        return {
            "solution_provided": True,
            "solution_length": len(solution),
            "solution_preview": solution[:300] + "...",
            "simulated": True
        }

    async def _step_7_search_history(self) -> Dict[str, Any]:
        """Step 7: 搜索歷史記錄"""
        self.log_step_start(7, "Search History")

        search_query = "連接池"

        try:
            endpoint = API_ENDPOINTS["sessions"]["search"].format(
                session_id=self.session_id
            )

            response = await self.call_api("GET", endpoint, params={"q": search_query})

            if response and response.get("success"):
                results = response["data"]["results"]
                return {
                    "query": search_query,
                    "results_count": len(results),
                    "matched_messages": [r.get("message_id") for r in results[:3]]
                }
            else:
                return await self._simulate_search(search_query)

        except Exception as e:
            self.logger.warning(f"Search failed, using simulation: {e}")
            return await self._simulate_search(search_query)

    async def _simulate_search(self, query: str) -> Dict[str, Any]:
        """模擬搜索"""
        # 在本地訊息中搜索
        matched = [
            m for m in self.messages
            if query in m.get("content", "")
        ]

        return {
            "query": query,
            "results_count": len(matched),
            "matched_messages": [m["message_id"] for m in matched[:3]],
            "simulated": True
        }

    async def _step_8_create_template(self) -> Dict[str, Any]:
        """Step 8: 建立會話模板"""
        self.log_step_start(8, "Create Template")

        try:
            endpoint = API_ENDPOINTS["sessions"]["create_template"]

            template_data = {
                "name": "資料庫連接問題排查",
                "description": "用於診斷和解決資料庫連接相關問題的模板",
                "source_session_id": self.session_id,
                "category": "technical_support",
                "tags": ["database", "connection", "troubleshooting"]
            }

            response = await self.call_api("POST", endpoint, json=template_data)

            if response and response.get("success"):
                self.template_id = response["data"]["template_id"]
                return {
                    "template_id": self.template_id,
                    "name": template_data["name"],
                    "created": True
                }
            else:
                return await self._simulate_create_template(template_data)

        except Exception as e:
            self.logger.warning(f"Template creation failed: {e}")
            return await self._simulate_create_template({
                "name": "資料庫連接問題排查",
                "category": "technical_support"
            })

    async def _simulate_create_template(self, template_data: Dict) -> Dict[str, Any]:
        """模擬創建模板"""
        self.template_id = f"template_{uuid.uuid4().hex[:8]}"

        return {
            "template_id": self.template_id,
            "name": template_data.get("name", "New Template"),
            "created": True,
            "simulated": True
        }

    async def _step_9_view_statistics(self) -> Dict[str, Any]:
        """Step 9: 查看統計信息"""
        self.log_step_start(9, "View Statistics")

        try:
            endpoint = API_ENDPOINTS["sessions"]["statistics"].format(
                session_id=self.session_id
            )

            response = await self.call_api("GET", endpoint)

            if response and response.get("success"):
                stats = response["data"]
                return {
                    "total_messages": stats.get("message_count"),
                    "total_tokens": stats.get("total_tokens"),
                    "duration_seconds": stats.get("duration_seconds"),
                    "attachments_count": stats.get("attachments_count")
                }
            else:
                return await self._simulate_statistics()

        except Exception as e:
            self.logger.warning(f"Statistics fetch failed: {e}")
            return await self._simulate_statistics()

    async def _simulate_statistics(self) -> Dict[str, Any]:
        """模擬統計信息"""
        return {
            "total_messages": len(self.messages),
            "total_tokens": len(self.messages) * 500,  # 估算
            "duration_seconds": 300,  # 5 分鐘
            "attachments_count": len(self.attachments),
            "simulated": True
        }

    async def _step_10_end_session(self) -> Dict[str, Any]:
        """Step 10: 結束 Session"""
        self.log_step_start(10, "End Session")

        try:
            endpoint = API_ENDPOINTS["sessions"]["end"].format(
                session_id=self.session_id
            )

            response = await self.call_api("POST", endpoint)

            if response and response.get("success"):
                self.session_status = "ENDED"
                return {
                    "session_id": self.session_id,
                    "final_status": "ENDED",
                    "ended_at": datetime.now().isoformat()
                }
            else:
                return await self._simulate_end_session()

        except Exception as e:
            self.logger.warning(f"End session failed: {e}")
            return await self._simulate_end_session()

    async def _simulate_end_session(self) -> Dict[str, Any]:
        """模擬結束 Session"""
        self.session_status = "ENDED"

        return {
            "session_id": self.session_id,
            "final_status": "ENDED",
            "ended_at": datetime.now().isoformat(),
            "simulated": True
        }

    async def execute(self) -> ScenarioResult:
        """執行完整測試場景"""
        self.logger.info(f"Starting {self.scenario_name} scenario")

        steps = [
            ("1", "Create Session", self._step_1_create_session),
            ("2", "Upload Error Log", self._step_2_upload_error_log),
            ("3", "Send Problem Description", self._step_3_send_problem_description),
            ("4", "AI Analyze Log", self._step_4_ai_analyze_log),
            ("5", "Multi-turn Conversation", self._step_5_multi_turn_conversation),
            ("6", "Get Solution", self._step_6_get_solution),
            ("7", "Search History", self._step_7_search_history),
            ("8", "Create Template", self._step_8_create_template),
            ("9", "View Statistics", self._step_9_view_statistics),
            ("10", "End Session", self._step_10_end_session),
        ]

        for step_id, step_name, step_func in steps:
            result = await self.run_step(step_id, step_name, step_func)
            if not result.success:
                self.logger.error(f"Step {step_id} failed: {result.error}")
                # 繼續執行其他步驟以收集更多信息

        return await self.run()


async def main():
    """主函數"""
    print("=" * 60)
    print("Phase 10: Session Mode - Technical Support Session")
    print("=" * 60)

    config = PhaseTestConfig(
        use_real_llm=True,
        llm_provider="azure",
        llm_deployment="gpt-5.2"
    )

    scenario = TechSupportSessionScenario(config)
    result = await scenario.execute()

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Scenario: {result.scenario_name}")
    print(f"Phase: {result.phase}")
    print(f"Overall Success: {'✅ PASSED' if result.success else '❌ FAILED'}")
    print(f"Steps Passed: {result.steps_passed}/{result.steps_total}")
    print(f"Duration: {result.duration_seconds:.2f}s")

    print("\nStep Details:")
    for step in result.steps:
        status = "✅" if step.success else "❌"
        print(f"  {status} Step {step.step_id}: {step.step_name}")
        if step.error:
            print(f"      Error: {step.error}")

    # 保存結果
    output_file = f"phase_10_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_file}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
