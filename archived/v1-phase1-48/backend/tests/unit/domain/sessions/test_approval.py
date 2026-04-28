"""
Tests for Tool Approval Manager (S46-4)

Sprint 46: Session-Agent Bridge
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import json

from src.domain.sessions.approval import (
    ApprovalStatus,
    ToolApprovalRequest,
    ToolApprovalManager,
    ApprovalNotFoundError,
    ApprovalAlreadyResolvedError,
    ApprovalExpiredError,
    create_approval_manager,
)


# ===== ApprovalStatus Tests =====

class TestApprovalStatus:
    """ApprovalStatus 枚舉測試"""

    def test_status_values(self):
        """測試狀態值"""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.EXPIRED.value == "expired"

    def test_status_string_enum(self):
        """測試字符串枚舉"""
        assert ApprovalStatus.PENDING == "pending"
        assert ApprovalStatus.APPROVED == "approved"


# ===== ToolApprovalRequest Tests =====

class TestToolApprovalRequest:
    """ToolApprovalRequest 數據類測試"""

    def test_create_request(self):
        """測試創建審批請求"""
        now = datetime.utcnow()
        request = ToolApprovalRequest(
            session_id="session-1",
            execution_id="exec-1",
            tool_call={"name": "test_tool", "arguments": {"arg1": "val1"}},
            created_at=now,
            expires_at=now + timedelta(seconds=300),
        )

        assert request.session_id == "session-1"
        assert request.execution_id == "exec-1"
        assert request.tool_call["name"] == "test_tool"
        assert request.status == ApprovalStatus.PENDING
        assert request.is_pending is True
        assert request.id is not None

    def test_is_pending_property(self):
        """測試 is_pending 屬性"""
        request = ToolApprovalRequest(status=ApprovalStatus.PENDING)
        assert request.is_pending is True

        request.status = ApprovalStatus.APPROVED
        assert request.is_pending is False

    def test_is_expired_property(self):
        """測試 is_expired 屬性"""
        # 未過期
        request = ToolApprovalRequest(
            expires_at=datetime.utcnow() + timedelta(seconds=300)
        )
        assert request.is_expired is False

        # 已過期
        request = ToolApprovalRequest(
            expires_at=datetime.utcnow() - timedelta(seconds=10)
        )
        assert request.is_expired is True

        # 狀態為 EXPIRED
        request = ToolApprovalRequest(
            status=ApprovalStatus.EXPIRED,
            expires_at=datetime.utcnow() + timedelta(seconds=300)
        )
        assert request.is_expired is True

    def test_time_remaining(self):
        """測試剩餘時間計算"""
        # 有剩餘時間
        request = ToolApprovalRequest(
            expires_at=datetime.utcnow() + timedelta(seconds=100)
        )
        remaining = request.time_remaining
        assert remaining.total_seconds() > 0
        assert remaining.total_seconds() <= 100

        # 已過期
        request = ToolApprovalRequest(
            expires_at=datetime.utcnow() - timedelta(seconds=10)
        )
        assert request.time_remaining == timedelta(0)

        # 非 pending 狀態
        request = ToolApprovalRequest(
            status=ApprovalStatus.APPROVED,
            expires_at=datetime.utcnow() + timedelta(seconds=100)
        )
        assert request.time_remaining == timedelta(0)

    def test_tool_name_property(self):
        """測試工具名稱屬性"""
        request = ToolApprovalRequest(
            tool_call={"name": "my_tool", "arguments": {}}
        )
        assert request.tool_name == "my_tool"

        # 空 tool_call
        request = ToolApprovalRequest(tool_call={})
        assert request.tool_name == ""

    def test_tool_arguments_property(self):
        """測試工具參數屬性"""
        request = ToolApprovalRequest(
            tool_call={"name": "tool", "arguments": {"key": "value"}}
        )
        assert request.tool_arguments == {"key": "value"}

    def test_to_dict(self):
        """測試轉換為字典"""
        now = datetime.utcnow()
        request = ToolApprovalRequest(
            id="req-1",
            session_id="session-1",
            execution_id="exec-1",
            tool_call={"name": "test"},
            created_at=now,
            expires_at=now + timedelta(seconds=300),
        )

        data = request.to_dict()

        assert data["id"] == "req-1"
        assert data["session_id"] == "session-1"
        assert data["execution_id"] == "exec-1"
        assert data["tool_call"] == {"name": "test"}
        assert data["status"] == "pending"
        assert data["resolved_at"] is None

    def test_from_dict(self):
        """測試從字典創建"""
        now = datetime.utcnow()
        data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "approved",
            "resolved_at": now.isoformat(),
            "resolved_by": "user-1",
            "feedback": "Looks good",
        }

        request = ToolApprovalRequest.from_dict(data)

        assert request.id == "req-1"
        assert request.session_id == "session-1"
        assert request.status == ApprovalStatus.APPROVED
        assert request.resolved_by == "user-1"
        assert request.feedback == "Looks good"

    def test_from_dict_defaults(self):
        """測試從字典創建 - 使用預設值"""
        data = {}
        request = ToolApprovalRequest.from_dict(data)

        assert request.status == ApprovalStatus.PENDING
        assert request.tool_call == {}


# ===== ToolApprovalManager Tests =====

@pytest.fixture
def mock_cache():
    """創建模擬快取"""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.setex = AsyncMock()
    cache.delete = AsyncMock(return_value=1)
    cache.keys = AsyncMock(return_value=[])
    return cache


@pytest.fixture
def approval_manager(mock_cache):
    """創建審批管理器"""
    return ToolApprovalManager(cache=mock_cache, default_timeout=300)


class TestToolApprovalManagerInit:
    """ToolApprovalManager 初始化測試"""

    def test_init_default_timeout(self, mock_cache):
        """測試預設超時"""
        manager = ToolApprovalManager(cache=mock_cache)
        assert manager._default_timeout == 300

    def test_init_custom_timeout(self, mock_cache):
        """測試自定義超時"""
        manager = ToolApprovalManager(cache=mock_cache, default_timeout=600)
        assert manager._default_timeout == 600


class TestToolApprovalManagerCreate:
    """ToolApprovalManager 創建審批請求測試"""

    @pytest.mark.asyncio
    async def test_create_approval_request(self, approval_manager, mock_cache):
        """測試創建審批請求"""
        tool_call = {"name": "test_tool", "arguments": {"arg": "val"}}

        request = await approval_manager.create_approval_request(
            session_id="session-1",
            execution_id="exec-1",
            tool_call=tool_call,
        )

        assert request.session_id == "session-1"
        assert request.execution_id == "exec-1"
        assert request.tool_call == tool_call
        assert request.status == ApprovalStatus.PENDING
        assert request.is_pending is True

        # 驗證存儲到 Redis
        mock_cache.setex.assert_called()

    @pytest.mark.asyncio
    async def test_create_with_custom_timeout(self, approval_manager, mock_cache):
        """測試自定義超時創建"""
        request = await approval_manager.create_approval_request(
            session_id="session-1",
            execution_id="exec-1",
            tool_call={"name": "tool"},
            timeout=600,
        )

        # 驗證過期時間約為 600 秒後
        remaining = (request.expires_at - request.created_at).total_seconds()
        assert 599 <= remaining <= 601


class TestToolApprovalManagerGet:
    """ToolApprovalManager 獲取審批請求測試"""

    @pytest.mark.asyncio
    async def test_get_approval_request_not_found(self, approval_manager, mock_cache):
        """測試獲取不存在的審批請求"""
        mock_cache.get.return_value = None

        request = await approval_manager.get_approval_request("nonexistent")
        assert request is None

    @pytest.mark.asyncio
    async def test_get_approval_request_found(self, approval_manager, mock_cache):
        """測試獲取存在的審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        request = await approval_manager.get_approval_request("req-1")

        assert request is not None
        assert request.id == "req-1"
        assert request.session_id == "session-1"
        assert request.status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_approval_request_expired(self, approval_manager, mock_cache):
        """測試獲取已過期的審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": (now - timedelta(seconds=600)).isoformat(),
            "expires_at": (now - timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        request = await approval_manager.get_approval_request("req-1")

        assert request is not None
        assert request.status == ApprovalStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_get_approval_request_invalid_json(self, approval_manager, mock_cache):
        """測試獲取無效 JSON 數據"""
        mock_cache.get.return_value = "invalid json"

        request = await approval_manager.get_approval_request("req-1")

        assert request is None
        mock_cache.delete.assert_called()


class TestToolApprovalManagerResolve:
    """ToolApprovalManager 解決審批請求測試"""

    @pytest.mark.asyncio
    async def test_resolve_approval_approved(self, approval_manager, mock_cache):
        """測試批准審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        request = await approval_manager.resolve_approval(
            approval_id="req-1",
            approved=True,
            resolved_by="user-1",
            feedback="Approved",
        )

        assert request.status == ApprovalStatus.APPROVED
        assert request.resolved_by == "user-1"
        assert request.feedback == "Approved"
        assert request.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_approval_rejected(self, approval_manager, mock_cache):
        """測試拒絕審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        request = await approval_manager.resolve_approval(
            approval_id="req-1",
            approved=False,
            resolved_by="user-1",
            feedback="Not allowed",
        )

        assert request.status == ApprovalStatus.REJECTED
        assert request.feedback == "Not allowed"

    @pytest.mark.asyncio
    async def test_resolve_approval_not_found(self, approval_manager, mock_cache):
        """測試解決不存在的審批請求"""
        mock_cache.get.return_value = None

        with pytest.raises(ApprovalNotFoundError):
            await approval_manager.resolve_approval(
                approval_id="nonexistent",
                approved=True,
                resolved_by="user-1",
            )

    @pytest.mark.asyncio
    async def test_resolve_approval_already_resolved(self, approval_manager, mock_cache):
        """測試解決已解決的審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "approved",
            "resolved_at": now.isoformat(),
            "resolved_by": "user-1",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        with pytest.raises(ApprovalAlreadyResolvedError):
            await approval_manager.resolve_approval(
                approval_id="req-1",
                approved=True,
                resolved_by="user-2",
            )

    @pytest.mark.asyncio
    async def test_resolve_approval_expired(self, approval_manager, mock_cache):
        """測試解決已過期的審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": (now - timedelta(seconds=600)).isoformat(),
            "expires_at": (now - timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        with pytest.raises(ApprovalExpiredError):
            await approval_manager.resolve_approval(
                approval_id="req-1",
                approved=True,
                resolved_by="user-1",
            )


class TestToolApprovalManagerApproveReject:
    """ToolApprovalManager approve/reject 方法測試"""

    @pytest.mark.asyncio
    async def test_approve_method(self, approval_manager, mock_cache):
        """測試 approve 方法"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        request = await approval_manager.approve(
            approval_id="req-1",
            approved_by="user-1",
        )

        assert request.status == ApprovalStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_method(self, approval_manager, mock_cache):
        """測試 reject 方法"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        request = await approval_manager.reject(
            approval_id="req-1",
            rejected_by="user-1",
            reason="Security risk",
        )

        assert request.status == ApprovalStatus.REJECTED
        assert request.feedback == "Security risk"


class TestToolApprovalManagerPending:
    """ToolApprovalManager 獲取待審批請求測試"""

    @pytest.mark.asyncio
    async def test_get_pending_approvals_empty(self, approval_manager, mock_cache):
        """測試獲取空的待審批列表"""
        mock_cache.get.return_value = None

        approvals = await approval_manager.get_pending_approvals("session-1")
        assert approvals == []

    @pytest.mark.asyncio
    async def test_get_pending_approvals_with_items(self, approval_manager, mock_cache):
        """測試獲取有項目的待審批列表"""
        now = datetime.utcnow()

        # 模擬 Session 的審批 ID 列表
        session_list = json.dumps(["req-1", "req-2"])

        # 模擬審批請求數據
        pending_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        approved_data = {
            "id": "req-2",
            "session_id": "session-1",
            "execution_id": "exec-2",
            "tool_call": {"name": "test2"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "approved",
        }

        # 設置 mock 返回值
        def get_side_effect(key):
            if "session:approvals:" in key:
                return session_list
            elif "req-1" in key:
                return json.dumps(pending_data)
            elif "req-2" in key:
                return json.dumps(approved_data)
            return None

        mock_cache.get.side_effect = get_side_effect

        approvals = await approval_manager.get_pending_approvals("session-1")

        assert len(approvals) == 1
        assert approvals[0].id == "req-1"
        assert approvals[0].status == ApprovalStatus.PENDING


class TestToolApprovalManagerCancel:
    """ToolApprovalManager 取消審批請求測試"""

    @pytest.mark.asyncio
    async def test_cancel_approval_success(self, approval_manager, mock_cache):
        """測試成功取消審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        result = await approval_manager.cancel_approval(
            approval_id="req-1",
            cancelled_by="user-1",
            reason="No longer needed",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_approval_not_found(self, approval_manager, mock_cache):
        """測試取消不存在的審批請求"""
        mock_cache.get.return_value = None

        result = await approval_manager.cancel_approval(
            approval_id="nonexistent",
            cancelled_by="user-1",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_approval_already_resolved(self, approval_manager, mock_cache):
        """測試取消已解決的審批請求"""
        now = datetime.utcnow()
        stored_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=300)).isoformat(),
            "status": "approved",
        }
        mock_cache.get.return_value = json.dumps(stored_data)

        result = await approval_manager.cancel_approval(
            approval_id="req-1",
            cancelled_by="user-1",
        )

        assert result is False


class TestToolApprovalManagerCleanup:
    """ToolApprovalManager 清理過期請求測試"""

    @pytest.mark.asyncio
    async def test_cleanup_expired_empty(self, approval_manager, mock_cache):
        """測試清理空列表"""
        mock_cache.keys.return_value = []

        count = await approval_manager.cleanup_expired()
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_with_session(self, approval_manager, mock_cache):
        """測試清理指定 Session 的過期請求"""
        now = datetime.utcnow()

        # 模擬數據
        session_list = json.dumps(["req-1"])
        expired_data = {
            "id": "req-1",
            "session_id": "session-1",
            "execution_id": "exec-1",
            "tool_call": {"name": "test"},
            "created_at": (now - timedelta(seconds=600)).isoformat(),
            "expires_at": (now - timedelta(seconds=300)).isoformat(),
            "status": "pending",
        }

        def get_side_effect(key):
            if "session:approvals:" in key:
                return session_list
            elif "req-1" in key:
                return json.dumps(expired_data)
            return None

        mock_cache.get.side_effect = get_side_effect

        count = await approval_manager.cleanup_expired(session_id="session-1")
        assert count == 1


class TestCreateApprovalManager:
    """create_approval_manager 工廠函數測試"""

    def test_create_approval_manager(self, mock_cache):
        """測試工廠函數"""
        manager = create_approval_manager(
            cache=mock_cache,
            default_timeout=600,
        )

        assert isinstance(manager, ToolApprovalManager)
        assert manager._default_timeout == 600

    def test_create_approval_manager_default(self, mock_cache):
        """測試工廠函數預設值"""
        manager = create_approval_manager(cache=mock_cache)
        assert manager._default_timeout == 300


# ===== Integration Tests =====

class TestToolApprovalManagerIntegration:
    """ToolApprovalManager 整合測試"""

    @pytest.mark.asyncio
    async def test_full_approval_workflow(self, mock_cache):
        """測試完整審批流程"""
        # 使用真實的內存存儲模擬
        storage = {}

        async def mock_get(key):
            return storage.get(key)

        async def mock_setex(key, ttl, value):
            storage[key] = value

        async def mock_delete(*keys):
            for key in keys:
                storage.pop(key, None)
            return len(keys)

        mock_cache.get.side_effect = mock_get
        mock_cache.setex.side_effect = mock_setex
        mock_cache.delete.side_effect = mock_delete

        manager = ToolApprovalManager(cache=mock_cache)

        # 1. 創建審批請求
        request = await manager.create_approval_request(
            session_id="session-1",
            execution_id="exec-1",
            tool_call={"name": "delete_file", "arguments": {"path": "/tmp/test"}},
            timeout=300,
        )
        assert request.status == ApprovalStatus.PENDING

        # 2. 獲取審批請求
        fetched = await manager.get_approval_request(request.id)
        assert fetched is not None
        assert fetched.id == request.id

        # 3. 批准審批請求
        approved = await manager.approve(
            approval_id=request.id,
            approved_by="admin",
            feedback="Verified safe operation",
        )
        assert approved.status == ApprovalStatus.APPROVED
        assert approved.resolved_by == "admin"

    @pytest.mark.asyncio
    async def test_rejection_workflow(self, mock_cache):
        """測試拒絕流程"""
        storage = {}

        async def mock_get(key):
            return storage.get(key)

        async def mock_setex(key, ttl, value):
            storage[key] = value

        mock_cache.get.side_effect = mock_get
        mock_cache.setex.side_effect = mock_setex

        manager = ToolApprovalManager(cache=mock_cache)

        # 創建並拒絕
        request = await manager.create_approval_request(
            session_id="session-1",
            execution_id="exec-1",
            tool_call={"name": "dangerous_tool", "arguments": {}},
        )

        rejected = await manager.reject(
            approval_id=request.id,
            rejected_by="security_admin",
            reason="This operation is not allowed in production",
        )

        assert rejected.status == ApprovalStatus.REJECTED
        assert rejected.feedback == "This operation is not allowed in production"
