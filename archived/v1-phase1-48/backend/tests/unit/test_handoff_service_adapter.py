# =============================================================================
# Test: HandoffService Adapter - Sprint 21 S21-4
# =============================================================================
# 測試 HandoffService 整合層
#
# 覆蓋範圍:
#   - HandoffServiceStatus 枚舉
#   - HandoffRequest, HandoffRecord 數據類
#   - HandoffTriggerResult, HandoffStatusResult, HandoffCancelResult
#   - HandoffService 核心功能
#   - Agent 註冊和能力匹配
#   - Handoff 生命週期管理
# =============================================================================

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.integrations.agent_framework.builders.handoff_service import (
    HandoffServiceStatus,
    HandoffRequest,
    HandoffRecord,
    HandoffTriggerResult,
    HandoffStatusResult,
    HandoffCancelResult,
    HandoffService,
    create_handoff_service,
)
from src.integrations.agent_framework.builders.handoff_policy import (
    LegacyHandoffPolicy,
)
from src.integrations.agent_framework.builders.handoff_capability import (
    MatchStrategy,
    AgentCapabilityInfo,
    CapabilityRequirementInfo,
    CapabilityCategory,
)


# =============================================================================
# Test: HandoffServiceStatus Enum
# =============================================================================


class TestHandoffServiceStatus:
    """測試服務狀態枚舉。"""

    def test_all_statuses_defined(self):
        """驗證所有狀態都已定義。"""
        expected_statuses = [
            "INITIATED",
            "MATCHING",
            "CONTEXT_TRANSFER",
            "EXECUTING",
            "WAITING_INPUT",
            "COMPLETED",
            "CANCELLED",
            "FAILED",
            "ROLLED_BACK",
        ]

        for status_name in expected_statuses:
            assert hasattr(HandoffServiceStatus, status_name)

    def test_status_values(self):
        """驗證狀態值。"""
        assert HandoffServiceStatus.INITIATED.value == "initiated"
        assert HandoffServiceStatus.COMPLETED.value == "completed"
        assert HandoffServiceStatus.FAILED.value == "failed"
        assert HandoffServiceStatus.CANCELLED.value == "cancelled"


# =============================================================================
# Test: HandoffRequest Data Class
# =============================================================================


class TestHandoffRequest:
    """測試 Handoff 請求數據類。"""

    def test_default_values(self):
        """驗證默認值。"""
        source_id = uuid4()
        request = HandoffRequest(source_agent_id=source_id)

        assert request.source_agent_id == source_id
        assert request.target_agent_id is None
        assert request.policy == LegacyHandoffPolicy.IMMEDIATE
        assert request.required_capabilities == []
        assert request.context == {}
        assert request.reason == ""
        assert request.metadata == {}
        assert request.match_strategy == MatchStrategy.BEST_FIT

    def test_custom_values(self):
        """驗證自定義值。"""
        source_id = uuid4()
        target_id = uuid4()

        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
            policy=LegacyHandoffPolicy.GRACEFUL,
            required_capabilities=["coding", "testing"],
            context={"task": "review"},
            reason="Needs specialist",
            metadata={"priority": "high"},
            match_strategy=MatchStrategy.LEAST_LOADED,
        )

        assert request.source_agent_id == source_id
        assert request.target_agent_id == target_id
        assert request.policy == LegacyHandoffPolicy.GRACEFUL
        assert request.required_capabilities == ["coding", "testing"]
        assert request.context == {"task": "review"}
        assert request.reason == "Needs specialist"
        assert request.metadata == {"priority": "high"}
        assert request.match_strategy == MatchStrategy.LEAST_LOADED


# =============================================================================
# Test: HandoffRecord Data Class
# =============================================================================


class TestHandoffRecord:
    """測試 Handoff 記錄數據類。"""

    def test_default_values(self):
        """驗證默認值。"""
        handoff_id = uuid4()
        source_id = uuid4()

        record = HandoffRecord(
            handoff_id=handoff_id,
            status=HandoffServiceStatus.INITIATED,
            source_agent_id=source_id,
            target_agent_id=None,
            policy=LegacyHandoffPolicy.IMMEDIATE,
            context={},
        )

        assert record.handoff_id == handoff_id
        assert record.status == HandoffServiceStatus.INITIATED
        assert record.source_agent_id == source_id
        assert record.target_agent_id is None
        assert record.progress == 0.0
        assert record.context_transferred is False
        assert record.completed_at is None
        assert record.error_message is None


# =============================================================================
# Test: HandoffService - Initialization
# =============================================================================


class TestHandoffServiceInit:
    """測試 HandoffService 初始化。"""

    def test_default_init(self):
        """驗證默認初始化。"""
        service = HandoffService()

        assert service.policy_adapter is not None
        assert service.capability_matcher is not None
        assert service.context_transfer is not None

    def test_factory_function(self):
        """驗證工廠函數。"""
        service = create_handoff_service()

        assert isinstance(service, HandoffService)


# =============================================================================
# Test: HandoffService - Agent Registration
# =============================================================================


class TestHandoffServiceAgentRegistration:
    """測試 Agent 註冊功能。"""

    def test_register_agent_capabilities(self):
        """驗證註冊 Agent 能力。"""
        service = HandoffService()
        agent_id = uuid4()

        capabilities = [
            AgentCapabilityInfo(
                name="coding",
                proficiency=0.9,
                category=CapabilityCategory.KNOWLEDGE,
            ),
            AgentCapabilityInfo(
                name="testing",
                proficiency=0.8,
            ),
        ]

        service.register_agent_capabilities(agent_id, capabilities)

        # 驗證能力已註冊
        registered = service.get_agent_capabilities(agent_id)
        assert len(registered) == 2
        assert registered[0].name == "coding"

    def test_update_agent_availability(self):
        """驗證更新 Agent 可用性。"""
        service = HandoffService()
        agent_id = uuid4()

        # 註冊能力
        service.register_agent_capabilities(
            agent_id,
            [AgentCapabilityInfo(name="coding", proficiency=0.9)],
        )

        # 更新可用性
        service.update_agent_availability(
            agent_id=agent_id,
            is_available=True,
            current_load=0.3,
        )

        # 無異常即為成功

    def test_unregister_agent(self):
        """驗證取消註冊 Agent。"""
        service = HandoffService()
        agent_id = uuid4()

        # 註冊
        service.register_agent_capabilities(
            agent_id,
            [AgentCapabilityInfo(name="coding", proficiency=0.9)],
        )

        # 取消註冊
        service.unregister_agent(agent_id)

        # 驗證已取消
        capabilities = service.get_agent_capabilities(agent_id)
        assert len(capabilities) == 0


# =============================================================================
# Test: HandoffService - Trigger Handoff
# =============================================================================


class TestHandoffServiceTrigger:
    """測試觸發 Handoff 功能。"""

    @pytest.mark.asyncio
    async def test_trigger_with_target(self):
        """驗證指定目標的 Handoff。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
            policy=LegacyHandoffPolicy.IMMEDIATE,
            reason="Direct handoff",
        )

        result = await service.trigger_handoff(request)

        assert result.handoff_id is not None
        assert result.status == HandoffServiceStatus.INITIATED
        assert result.source_agent_id == source_id
        assert result.target_agent_id == target_id
        assert result.message == "Handoff initiated successfully"

    @pytest.mark.asyncio
    async def test_trigger_with_auto_match(self):
        """驗證自動匹配的 Handoff。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        # 註冊目標 Agent 能力
        service.register_agent_capabilities(
            target_id,
            [
                AgentCapabilityInfo(name="coding", proficiency=0.9),
                AgentCapabilityInfo(name="testing", proficiency=0.8),
            ],
        )
        service.update_agent_availability(target_id, is_available=True)

        request = HandoffRequest(
            source_agent_id=source_id,
            required_capabilities=["coding"],
            policy=LegacyHandoffPolicy.IMMEDIATE,
        )

        result = await service.trigger_handoff(request)

        assert result.handoff_id is not None
        assert result.status == HandoffServiceStatus.INITIATED
        # 注意：自動匹配時 target_agent_id 返回為字串
        assert result.target_agent_id == str(target_id)
        assert result.match_result is not None

    @pytest.mark.asyncio
    async def test_trigger_with_different_policies(self):
        """驗證不同政策的 Handoff。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        # 測試 IMMEDIATE 和 GRACEFUL 政策
        # CONDITIONAL 政策需要 condition_evaluator，在此簡化測試
        for policy in [LegacyHandoffPolicy.IMMEDIATE, LegacyHandoffPolicy.GRACEFUL]:
            request = HandoffRequest(
                source_agent_id=source_id,
                target_agent_id=target_id,
                policy=policy,
            )

            result = await service.trigger_handoff(request)
            assert result.status == HandoffServiceStatus.INITIATED


# =============================================================================
# Test: HandoffService - Execute Handoff
# =============================================================================


class TestHandoffServiceExecute:
    """測試執行 Handoff 功能。"""

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """驗證成功執行 Handoff。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        # 觸發
        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context={"task": "test"},
        )
        trigger_result = await service.trigger_handoff(request)

        # 執行
        execution_result = await service.execute_handoff(
            trigger_result.handoff_id,
            context_data={"additional": "data"},
        )

        assert execution_result.status.value == "completed"

    @pytest.mark.asyncio
    async def test_execute_not_found(self):
        """驗證執行不存在的 Handoff 拋出錯誤。"""
        service = HandoffService()

        with pytest.raises(ValueError) as exc_info:
            await service.execute_handoff(uuid4())

        assert "not found" in str(exc_info.value)


# =============================================================================
# Test: HandoffService - Get Status
# =============================================================================


class TestHandoffServiceStatus:
    """測試獲取 Handoff 狀態功能。"""

    @pytest.mark.asyncio
    async def test_get_status_success(self):
        """驗證獲取狀態成功。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        # 觸發
        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
        )
        trigger_result = await service.trigger_handoff(request)

        # 獲取狀態
        status = service.get_handoff_status(trigger_result.handoff_id)

        assert status is not None
        assert status.handoff_id == trigger_result.handoff_id
        assert status.status == HandoffServiceStatus.INITIATED
        assert status.source_agent_id == source_id

    def test_get_status_not_found(self):
        """驗證獲取不存在的 Handoff 返回 None。"""
        service = HandoffService()

        status = service.get_handoff_status(uuid4())
        assert status is None


# =============================================================================
# Test: HandoffService - Cancel Handoff
# =============================================================================


class TestHandoffServiceCancel:
    """測試取消 Handoff 功能。"""

    @pytest.mark.asyncio
    async def test_cancel_success(self):
        """驗證取消成功。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        # 觸發
        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
        )
        trigger_result = await service.trigger_handoff(request)

        # 取消
        cancel_result = await service.cancel_handoff(
            trigger_result.handoff_id,
            reason="Changed my mind",
        )

        assert cancel_result.handoff_id == trigger_result.handoff_id
        assert cancel_result.status == HandoffServiceStatus.CANCELLED
        assert cancel_result.rollback_performed is False
        assert "cancelled" in cancel_result.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_with_rollback(self):
        """驗證需要回滾的取消。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        # 觸發並執行 (會設置 context_transferred)
        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
        )
        trigger_result = await service.trigger_handoff(request)

        # 手動設置 context_transferred 為 True 模擬傳輸完成後取消
        service._handoffs[trigger_result.handoff_id].context_transferred = True

        # 取消
        cancel_result = await service.cancel_handoff(trigger_result.handoff_id)

        assert cancel_result.status == HandoffServiceStatus.ROLLED_BACK
        assert cancel_result.rollback_performed is True

    @pytest.mark.asyncio
    async def test_cancel_not_found(self):
        """驗證取消不存在的 Handoff 拋出錯誤。"""
        service = HandoffService()

        with pytest.raises(ValueError) as exc_info:
            await service.cancel_handoff(uuid4())

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancel_completed_fails(self):
        """驗證取消已完成的 Handoff 拋出錯誤。"""
        service = HandoffService()
        source_id = uuid4()
        target_id = uuid4()

        # 觸發並執行 (需要提供有效的上下文)
        request = HandoffRequest(
            source_agent_id=source_id,
            target_agent_id=target_id,
            context={"task_state": {"status": "running"}},  # 添加必需的 task_state
        )
        trigger_result = await service.trigger_handoff(request)
        await service.execute_handoff(
            trigger_result.handoff_id,
            context_data={"task_state": {"status": "done"}},
        )

        # 嘗試取消已完成的 handoff
        with pytest.raises(ValueError) as exc_info:
            await service.cancel_handoff(trigger_result.handoff_id)

        assert "cannot be cancelled" in str(exc_info.value)


# =============================================================================
# Test: HandoffService - Get History
# =============================================================================


class TestHandoffServiceHistory:
    """測試獲取 Handoff 歷史功能。"""

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        """驗證空歷史。"""
        service = HandoffService()

        records, total = service.get_handoff_history()

        assert records == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_history_with_records(self):
        """驗證有記錄的歷史。"""
        service = HandoffService()
        source_id = uuid4()

        # 創建多個 handoff
        for i in range(5):
            request = HandoffRequest(
                source_agent_id=source_id,
                target_agent_id=uuid4(),
            )
            await service.trigger_handoff(request)

        records, total = service.get_handoff_history()

        assert len(records) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_history_filter_by_source(self):
        """驗證按來源過濾。"""
        service = HandoffService()
        source_id1 = uuid4()
        source_id2 = uuid4()

        # 創建不同來源的 handoff
        for _ in range(3):
            await service.trigger_handoff(
                HandoffRequest(source_agent_id=source_id1, target_agent_id=uuid4())
            )

        for _ in range(2):
            await service.trigger_handoff(
                HandoffRequest(source_agent_id=source_id2, target_agent_id=uuid4())
            )

        records, total = service.get_handoff_history(source_agent_id=source_id1)

        assert len(records) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_history_pagination(self):
        """驗證分頁。"""
        service = HandoffService()
        source_id = uuid4()

        # 創建 10 個 handoff
        for _ in range(10):
            await service.trigger_handoff(
                HandoffRequest(source_agent_id=source_id, target_agent_id=uuid4())
            )

        # 第一頁
        records, total = service.get_handoff_history(page=1, page_size=3)
        assert len(records) == 3
        assert total == 10

        # 第二頁
        records, total = service.get_handoff_history(page=2, page_size=3)
        assert len(records) == 3

        # 最後一頁
        records, total = service.get_handoff_history(page=4, page_size=3)
        assert len(records) == 1


# =============================================================================
# Test: HandoffService - Find Matching Agents
# =============================================================================


class TestHandoffServiceMatching:
    """測試查找匹配 Agent 功能。"""

    def test_find_matching_agents(self):
        """驗證查找匹配 Agent。"""
        service = HandoffService()

        # 註冊多個 Agent
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()

        service.register_agent_capabilities(
            agent1,
            [
                AgentCapabilityInfo(name="coding", proficiency=0.9),
                AgentCapabilityInfo(name="testing", proficiency=0.8),
            ],
        )
        service.register_agent_capabilities(
            agent2,
            [
                AgentCapabilityInfo(name="coding", proficiency=0.7),
            ],
        )
        service.register_agent_capabilities(
            agent3,
            [
                AgentCapabilityInfo(name="design", proficiency=0.9),
            ],
        )

        # 更新可用性
        for agent_id in [agent1, agent2, agent3]:
            service.update_agent_availability(agent_id, is_available=True)

        # 查找
        requirements = [
            CapabilityRequirementInfo(
                name="coding",
                min_proficiency=0.5,
                required=True,
            ),
        ]

        matches = service.find_matching_agents(requirements)

        assert len(matches) >= 2
        # agent1 應該排在前面（proficiency 更高）
        # 注意：agent_id 返回為字串
        assert matches[0].agent_id == str(agent1)

    def test_find_matching_with_exclusion(self):
        """驗證排除特定 Agent。"""
        service = HandoffService()

        agent1 = uuid4()
        agent2 = uuid4()

        service.register_agent_capabilities(
            agent1,
            [AgentCapabilityInfo(name="coding", proficiency=0.9)],
        )
        service.register_agent_capabilities(
            agent2,
            [AgentCapabilityInfo(name="coding", proficiency=0.8)],
        )

        for agent_id in [agent1, agent2]:
            service.update_agent_availability(agent_id, is_available=True)

        requirements = [
            CapabilityRequirementInfo(
                name="coding",
                min_proficiency=0.5,
                required=True,
            ),
        ]

        # 排除 agent1
        matches = service.find_matching_agents(
            requirements,
            exclude_agents={agent1},
        )

        assert len(matches) == 1
        # 注意：agent_id 返回為字串
        assert matches[0].agent_id == str(agent2)


# =============================================================================
# Test: Factory Function
# =============================================================================


class TestHandoffServiceFactory:
    """測試工廠函數。"""

    def test_create_handoff_service(self):
        """驗證創建服務。"""
        service = create_handoff_service()

        assert isinstance(service, HandoffService)
        assert service.policy_adapter is not None
        assert service.capability_matcher is not None
        assert service.context_transfer is not None
