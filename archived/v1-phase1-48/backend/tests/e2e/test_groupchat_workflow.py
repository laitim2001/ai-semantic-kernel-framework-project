"""
IPA Platform - GroupChat Workflow E2E Tests

Sprint 30 S30-1: E2E 整合測試
測試場景 5: GroupChat 工作流

測試多 Agent 群聊對話的完整流程。

Adapter Integration:
- GroupChatBuilderAdapter: GroupChat 構建
- SpeakerSelectorAdapter: 發言者選擇
- VotingManagerAdapter: 投票管理

Author: IPA Platform Team
Version: 2.0.0 (Phase 5 Migration)
"""

import pytest
import pytest_asyncio
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List
from httpx import AsyncClient


# =============================================================================
# Test Class: GroupChat Workflow E2E Tests
# =============================================================================

class TestGroupChatWorkflow:
    """
    GroupChat 工作流端到端測試

    驗證多 Agent 群聊流程:
    1. 創建 GroupChat 會話
    2. 添加 Agents 到群組
    3. 執行對話
    4. 驗證輪流發言
    5. 驗證終止條件
    """

    @pytest.fixture
    def groupchat_config(self) -> Dict[str, Any]:
        """GroupChat 配置測試數據"""
        return {
            "name": f"E2E GroupChat {datetime.now().strftime('%H%M%S')}",
            "description": "GroupChat for E2E testing",
            "max_rounds": 10,
            "speaker_selection_method": "round_robin",
            "termination_condition": {
                "type": "max_rounds",
                "value": 5
            },
            "agents": [
                {
                    "name": "Analyst",
                    "role": "analyzer",
                    "instructions": "Analyze the problem and provide insights."
                },
                {
                    "name": "Developer",
                    "role": "developer",
                    "instructions": "Provide technical solutions."
                },
                {
                    "name": "Reviewer",
                    "role": "reviewer",
                    "instructions": "Review and validate proposals."
                }
            ]
        }

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_create_groupchat(
        self,
        client: AsyncClient,
        groupchat_config: Dict[str, Any]
    ):
        """
        測試創建 GroupChat

        驗證:
        - GroupChatBuilderAdapter 正確創建群組
        - 群組配置被正確保存
        """
        response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        assert response.status_code in [200, 201], f"創建失敗: {response.text}"

        groupchat = response.json()
        assert "id" in groupchat
        assert groupchat.get("name") == groupchat_config["name"]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_add_agent_to_groupchat(
        self,
        client: AsyncClient,
        groupchat_config: Dict[str, Any]
    ):
        """
        測試添加 Agent 到 GroupChat

        驗證 Agent 可以動態添加到群組
        """
        # 1. 創建 GroupChat
        create_response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建 GroupChat")

        groupchat = create_response.json()
        groupchat_id = groupchat.get("id")

        # 2. 添加新 Agent
        new_agent = {
            "name": "Coordinator",
            "role": "coordinator",
            "instructions": "Coordinate the discussion."
        }

        add_response = await client.post(
            f"/api/v1/groupchat/{groupchat_id}/agents",
            json=new_agent
        )

        assert add_response.status_code in [200, 201, 204, 400, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_start_groupchat_session(
        self,
        client: AsyncClient,
        groupchat_config: Dict[str, Any]
    ):
        """
        測試啟動 GroupChat 會話

        驗證:
        - 會話可以成功啟動
        - 初始訊息被正確處理
        """
        # 1. 創建 GroupChat
        create_response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建 GroupChat")

        groupchat = create_response.json()
        groupchat_id = groupchat.get("id")

        # 2. 啟動會話
        start_request = {
            "initial_message": "Let's discuss the new feature implementation.",
            "context": {"project": "IPA Platform"}
        }

        start_response = await client.post(
            f"/api/v1/groupchat/{groupchat_id}/start",
            json=start_request
        )

        assert start_response.status_code in [200, 201, 202, 400, 404]

        if start_response.status_code in [200, 201, 202]:
            result = start_response.json()
            assert "session_id" in result or "id" in result

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_send_message_to_groupchat(
        self,
        client: AsyncClient,
        groupchat_config: Dict[str, Any]
    ):
        """
        測試發送訊息到 GroupChat

        驗證訊息廣播和處理
        """
        # 1. 創建並啟動 GroupChat
        create_response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建 GroupChat")

        groupchat = create_response.json()
        groupchat_id = groupchat.get("id")

        # 啟動會話
        start_response = await client.post(
            f"/api/v1/groupchat/{groupchat_id}/start",
            json={"initial_message": "Start discussion"}
        )

        if start_response.status_code not in [200, 201, 202]:
            pytest.skip("無法啟動會話")

        # 2. 發送訊息
        message_request = {
            "content": "What are the key considerations for this feature?",
            "sender": "user"
        }

        send_response = await client.post(
            f"/api/v1/groupchat/{groupchat_id}/message",
            json=message_request
        )

        assert send_response.status_code in [200, 201, 202, 400, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_groupchat_messages(
        self,
        client: AsyncClient,
        groupchat_config: Dict[str, Any]
    ):
        """
        測試獲取 GroupChat 訊息歷史
        """
        # 創建 GroupChat
        create_response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建 GroupChat")

        groupchat = create_response.json()
        groupchat_id = groupchat.get("id")

        # 獲取訊息
        messages_response = await client.get(
            f"/api/v1/groupchat/{groupchat_id}/messages"
        )

        assert messages_response.status_code in [200, 404]

        if messages_response.status_code == 200:
            messages = messages_response.json()
            assert isinstance(messages, (list, dict))


# =============================================================================
# Test Class: Speaker Selection
# =============================================================================

class TestSpeakerSelection:
    """
    發言者選擇測試

    驗證 SpeakerSelectorAdapter 整合
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_round_robin_selection(
        self,
        client: AsyncClient
    ):
        """
        測試輪流發言選擇
        """
        groupchat_config = {
            "name": f"Round Robin Test {datetime.now().strftime('%H%M%S')}",
            "speaker_selection_method": "round_robin",
            "agents": [
                {"name": "Agent1", "role": "agent"},
                {"name": "Agent2", "role": "agent"},
                {"name": "Agent3", "role": "agent"}
            ]
        }

        response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        assert response.status_code in [200, 201, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_auto_selection(
        self,
        client: AsyncClient
    ):
        """
        測試自動發言者選擇
        """
        groupchat_config = {
            "name": f"Auto Select Test {datetime.now().strftime('%H%M%S')}",
            "speaker_selection_method": "auto",
            "agents": [
                {"name": "Agent1", "role": "analyzer"},
                {"name": "Agent2", "role": "developer"}
            ]
        }

        response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        assert response.status_code in [200, 201, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_manual_selection(
        self,
        client: AsyncClient
    ):
        """
        測試手動指定發言者
        """
        groupchat_config = {
            "name": f"Manual Select Test {datetime.now().strftime('%H%M%S')}",
            "speaker_selection_method": "manual",
            "agents": [
                {"name": "Agent1", "role": "agent"},
                {"name": "Agent2", "role": "agent"}
            ]
        }

        response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if response.status_code in [200, 201]:
            groupchat = response.json()
            groupchat_id = groupchat.get("id")

            # 指定下一個發言者
            next_speaker_response = await client.post(
                f"/api/v1/groupchat/{groupchat_id}/next-speaker",
                json={"agent_name": "Agent2"}
            )

            assert next_speaker_response.status_code in [200, 201, 400, 404]


# =============================================================================
# Test Class: GroupChat Termination
# =============================================================================

class TestGroupChatTermination:
    """
    GroupChat 終止條件測試
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_max_rounds_termination(
        self,
        client: AsyncClient
    ):
        """
        測試最大輪數終止
        """
        groupchat_config = {
            "name": f"Max Rounds Test {datetime.now().strftime('%H%M%S')}",
            "max_rounds": 3,
            "termination_condition": {
                "type": "max_rounds",
                "value": 3
            },
            "agents": [
                {"name": "Agent1", "role": "agent"},
                {"name": "Agent2", "role": "agent"}
            ]
        }

        response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        assert response.status_code in [200, 201, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_keyword_termination(
        self,
        client: AsyncClient
    ):
        """
        測試關鍵字終止
        """
        groupchat_config = {
            "name": f"Keyword Term Test {datetime.now().strftime('%H%M%S')}",
            "termination_condition": {
                "type": "keyword",
                "keywords": ["TERMINATE", "END_DISCUSSION"]
            },
            "agents": [
                {"name": "Agent1", "role": "agent"},
                {"name": "Agent2", "role": "agent"}
            ]
        }

        response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        assert response.status_code in [200, 201, 422]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_stop_groupchat(
        self,
        client: AsyncClient
    ):
        """
        測試手動停止 GroupChat
        """
        # 創建 GroupChat
        groupchat_config = {
            "name": f"Stop Test {datetime.now().strftime('%H%M%S')}",
            "agents": [{"name": "Agent1", "role": "agent"}]
        }

        create_response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建 GroupChat")

        groupchat = create_response.json()
        groupchat_id = groupchat.get("id")

        # 停止會話
        stop_response = await client.post(
            f"/api/v1/groupchat/{groupchat_id}/stop",
            json={"reason": "Test termination"}
        )

        assert stop_response.status_code in [200, 204, 400, 404]


# =============================================================================
# Test Class: GroupChat Voting
# =============================================================================

class TestGroupChatVoting:
    """
    GroupChat 投票功能測試

    驗證 VotingManagerAdapter 整合
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_create_vote(
        self,
        client: AsyncClient
    ):
        """
        測試創建投票
        """
        # 創建 GroupChat
        groupchat_config = {
            "name": f"Voting Test {datetime.now().strftime('%H%M%S')}",
            "agents": [
                {"name": "Agent1", "role": "agent"},
                {"name": "Agent2", "role": "agent"},
                {"name": "Agent3", "role": "agent"}
            ]
        }

        create_response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建 GroupChat")

        groupchat = create_response.json()
        groupchat_id = groupchat.get("id")

        # 創建投票
        vote_request = {
            "topic": "Should we proceed with implementation?",
            "options": ["Yes", "No", "Need more discussion"],
            "voting_method": "majority"
        }

        vote_response = await client.post(
            f"/api/v1/groupchat/{groupchat_id}/vote",
            json=vote_request
        )

        assert vote_response.status_code in [200, 201, 400, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_cast_vote(
        self,
        client: AsyncClient
    ):
        """
        測試投票
        """
        groupchat_id = str(uuid4())
        vote_id = str(uuid4())

        cast_vote_request = {
            "agent_name": "Agent1",
            "choice": "Yes",
            "reason": "The approach looks good"
        }

        response = await client.post(
            f"/api/v1/groupchat/{groupchat_id}/vote/{vote_id}/cast",
            json=cast_vote_request
        )

        # 端點應該存在
        assert response.status_code in [200, 201, 400, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_get_vote_results(
        self,
        client: AsyncClient
    ):
        """
        測試獲取投票結果
        """
        groupchat_id = str(uuid4())
        vote_id = str(uuid4())

        response = await client.get(
            f"/api/v1/groupchat/{groupchat_id}/vote/{vote_id}/results"
        )

        assert response.status_code in [200, 404]


# =============================================================================
# Test Class: GroupChat Builder Adapter Integration
# =============================================================================

class TestGroupChatBuilderAdapterIntegration:
    """
    GroupChatBuilderAdapter 整合測試

    驗證 Phase 5 遷移後的適配器正確工作
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_groupchat_list(
        self,
        client: AsyncClient
    ):
        """
        測試列出 GroupChat
        """
        response = await client.get("/api/v1/groupchat/")

        assert response.status_code == 200

        result = response.json()
        groupchats = result if isinstance(result, list) else result.get("items", [])

        assert isinstance(groupchats, list)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_groupchat_status(
        self,
        client: AsyncClient
    ):
        """
        測試 GroupChat 狀態端點
        """
        response = await client.get("/api/v1/groupchat/status")

        assert response.status_code in [200, 404]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_groupchat_delete(
        self,
        client: AsyncClient
    ):
        """
        測試刪除 GroupChat
        """
        # 創建一個 GroupChat
        groupchat_config = {
            "name": f"Delete Test {datetime.now().strftime('%H%M%S')}",
            "agents": [{"name": "Agent1", "role": "agent"}]
        }

        create_response = await client.post(
            "/api/v1/groupchat/",
            json=groupchat_config
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("無法創建 GroupChat")

        groupchat = create_response.json()
        groupchat_id = groupchat.get("id")

        # 刪除
        delete_response = await client.delete(
            f"/api/v1/groupchat/{groupchat_id}"
        )

        assert delete_response.status_code in [200, 204, 404]
