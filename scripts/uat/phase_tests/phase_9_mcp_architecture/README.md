# Phase 9: MCP Architecture 測試

## 概述

Phase 9 測試驗證 MCP (Model Context Protocol) 架構的完整功能，包括工具調用、權限管理和審計日誌。

## 測試場景

### 場景：雲端基礎設施診斷 (Cloud Infrastructure Diagnostics)

**業務背景**：
IT 運維團隊收到警報，需要診斷 Azure 虛擬機的問題。使用 AI 驅動的 MCP 工具進行自動化診斷。

**測試流程**：

```
Step 1: 連接 Azure MCP Server
    └─ MCPClient 連接到已註冊的 Azure Server

Step 2: 列出可用工具
    └─ 獲取所有可用的 Azure 操作工具

Step 3: 查詢 VM 清單
    └─ 使用 list_vms 工具獲取所有 VM

Step 4: 檢查特定 VM 狀態
    └─ 使用 get_vm_status 檢查問題 VM

Step 5: 權限檢查 (高風險操作)
    └─ 嘗試執行需要審批的操作

Step 6: 審計日誌驗證
    └─ 查詢並驗證操作審計記錄

Step 7: AI 驅動診斷分析
    └─ 使用真實 AI 分析診斷結果

Step 8: 斷開連接
    └─ 正確關閉 MCP 連接
```

## 測試的 MCP 組件

| 組件 | 功能 |
|------|------|
| MCPClient | 管理 MCP Server 連接 |
| MCPProtocol | JSON-RPC 2.0 協議實現 |
| MCPServerRegistry | Server 註冊和發現 |
| MCPPermissionManager | 三級權限控制 |
| MCPAuditLogger | 操作審計記錄 |
| Azure MCP Server | Azure 資源操作工具 |

## Azure MCP Server 工具

| 工具 | 風險等級 | 說明 |
|------|----------|------|
| list_vms | LOW | 列出所有 VM |
| get_vm | LOW | 獲取 VM 詳情 |
| get_vm_status | LOW | 獲取 VM 狀態 |
| start_vm | MEDIUM | 啟動 VM |
| stop_vm | MEDIUM | 停止 VM |
| restart_vm | MEDIUM | 重啟 VM |
| run_command | HIGH | 在 VM 上執行命令 |

## 執行方式

```bash
cd scripts/uat/phase_tests
python -m phase_9_mcp_architecture.scenario_infra_diagnostics
```

## 預期結果

1. **連接成功**: MCPClient 成功連接到 Azure MCP Server
2. **工具發現**: 能夠列出所有可用工具
3. **工具調用**: 成功執行 VM 查詢操作
4. **權限控制**: 高風險操作正確觸發審批流程
5. **審計記錄**: 所有操作被正確記錄

## 權限等級

```yaml
risk_levels:
  LOW: 1      # 只讀操作，無需審批
  MEDIUM: 2   # 低風險寫入，需要 Agent 確認
  HIGH: 3     # 危險操作，需要人工審批

approval_levels:
  NONE: 0     # 無需審批
  AGENT: 1    # Agent 自動審批
  HUMAN: 2    # 需要人工審批
```

## 依賴

- Azure SDK
- Azure 訂閱 ID 和資源群組
- 有效的 Azure 認證

---

**建立日期**: 2025-12-22
