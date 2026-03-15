# Dr. Frontend — IPA Platform 前端架構深度分析

**Generated**: 2026-03-15
**Analyst**: Dr. Frontend (Frontend Architecture Specialist)
**Scope**: `frontend/src/` — 200 source files (excl. tests), ~49,143 LOC
**Tech Stack**: React 18 + TypeScript 5 + Vite 5 + Zustand 4 + TanStack Query 5 + Tailwind CSS 3

---

## Executive Summary

IPA Platform 前端是一個功能豐富的企業級 React 應用程式，歷經 29 個 Phase、133+ Sprints 的迭代開發。整體架構品質中上，TypeScript 類型紀律極為優異（幾乎零 `any` 使用），元件結構清晰，Zustand + React Query 的雙軌狀態管理策略正確。

**核心優勢**：
- TypeScript 類型安全性極高（全 codebase 僅 1 個 `as any`）
- API Client 設計乾淨，統一的 Fetch API 封裝
- 自定義 Hooks 豐富（17 個），邏輯抽離做得好
- Shadcn UI + Tailwind 樣式系統一致

**關鍵問題**：
- **8 個超大元件/Hook**（>500 行），最大 1,313 行，急需拆分
- **零 Code Splitting**（無 `React.lazy`），所有路由同步載入
- **store/ vs stores/ 雙目錄**架構不一致
- **Create/Edit 頁面 ~80% 程式碼重複**（3,900 行可壓縮至 ~1,500 行）
- **Error Boundary 覆蓋不足**，僅包裹 ChatArea
- **10+ 頁面靜默降級為 mock 資料**，無視覺指示
- **49 個 console.log** 留在生產程式碼中

**嚴重度分布**：CRITICAL 3 / HIGH 6 / MEDIUM 8 / LOW 5 = 共 22 個前端架構問題

---

## 1. 元件架構分析

### 1.1 元件層次結構

```
App.tsx (Router)
├── LoginPage / SignupPage          (公開路由)
├── AGUIDemoPage / SwarmTestPage    (獨立全螢幕)
└── ProtectedRoute > AppLayout      (受保護路由)
    ├── Header + Sidebar + UserMenu
    ├── DashboardPage / PerformancePage
    ├── UnifiedChat                  (主聊天介面 — 最複雜)
    │   ├── ChatHeader
    │   ├── ChatHistoryPanel
    │   ├── ChatArea > MessageList
    │   ├── ChatInput + FileUpload
    │   ├── OrchestrationPanel
    │   ├── WorkflowSidePanel
    │   ├── StatusBar
    │   └── agent-swarm/ (15 元件)
    ├── Agents (CRUD 4 頁)
    ├── Workflows (CRUD 4 頁 + Editor)
    ├── Templates / Approvals / Audit
    └── DevUI (6 頁 + 嵌套佈局)
```

**元件總量統計**：

| 分類 | 元件數 | 佔比 |
|------|--------|------|
| unified-chat/ | 27 | 17.6% |
| agent-swarm/ | 15 | 9.8% |
| ag-ui/ | 13 | 8.5% |
| DevUI/ | 15 | 9.8% |
| ui/ (Shadcn) | 18 | 11.8% |
| workflow-editor/ | 7 | 4.6% |
| pages/ | 25+ | 16.3% |
| layout + shared + auth | 8 | 5.2% |
| hooks | 17 | 11.1% |
| stores | 3 | 2.0% |
| **Total** | **~153** | **100%** |

### 1.2 大型元件/Hook 清單（>300 行）— CRITICAL

以下檔案超過合理的單檔案上限（建議 <300 行），存在 **職責過多** 和 **可測試性差** 的風險：

| 排名 | 檔案 | 行數 | 嚴重度 | 問題 |
|------|------|------|--------|------|
| 1 | `hooks/useUnifiedChat.ts` | **1,313** | CRITICAL | 包含 SSE 連線、訊息處理、工具追蹤、審批流程、模式切換、歷史載入 — 至少 6 個職責 |
| 2 | `pages/workflows/EditWorkflowPage.tsx` | **1,040** | HIGH | 表單邏輯 + 驗證 + 佈局全部耦合 |
| 3 | `pages/agents/CreateAgentPage.tsx` | **1,015** | HIGH | 與 EditAgentPage (958L) 高度重複 |
| 4 | `hooks/useAGUI.ts` | **982** | HIGH | AG-UI 協議全部邏輯集中在單一 Hook |
| 5 | `pages/agents/EditAgentPage.tsx` | **958** | HIGH | 與 CreateAgentPage 80% 重複 |
| 6 | `pages/UnifiedChat.tsx` | **899** | HIGH | 頁面元件包含過多業務邏輯 |
| 7 | `pages/workflows/CreateWorkflowPage.tsx` | **887** | HIGH | 與 EditWorkflowPage 80% 重複 |
| 8 | `pages/SwarmTestPage.tsx` | **844** | MEDIUM | 測試頁面，可接受但建議抽取 |
| 9 | `hooks/useSwarmMock.ts` | **623** | MEDIUM | Mock hook，僅開發用 |
| 10 | `hooks/useSwarmReal.ts` | **603** | MEDIUM | 可拆分為更小的子 hook |
| 11 | `pages/DevUI/TraceDetail.tsx` | **562** | MEDIUM | 複雜頁面但職責單一 |
| 12 | `stores/unifiedChatStore.ts` | **508** | MEDIUM | Store 過大，可按功能拆分 |
| 13 | `components/unified-chat/OrchestrationPanel.tsx` | **508** | MEDIUM | 面板元件過大 |
| 14 | `types/unified-chat.ts` | **505** | LOW | 類型檔案，大小可接受 |

**建議拆分策略（useUnifiedChat.ts 為例）**：

```
useUnifiedChat.ts (1,313L) →
├── useSSEConnection.ts      (~200L) — SSE 連線管理 + 自動重連
├── useMessageHandler.ts     (~200L) — 訊息接收/發送/串流
├── useToolCallTracker.ts    (~150L) — 工具呼叫追蹤
├── useApprovalHandler.ts    (~150L) — HITL 審批邏輯
├── useModeManager.ts        (~100L) — 模式偵測 + 切換
├── useChatHistory.ts        (~100L) — 歷史載入/持久化
└── useUnifiedChat.ts        (~200L) — 組合層，串接以上 hooks
```

### 1.3 元件重用性評估

**良好的重用模式**：
- `components/shared/` 提供 `EmptyState`, `LoadingSpinner`, `StatusBadge` — 通用元件
- `components/ui/` 18 個 Shadcn 元件作為設計系統基礎
- `hooks/index.ts` 統一匯出，提供乾淨的 API 表面

**重用性不足的區域**：

| 問題 | 影響範圍 | 建議 |
|------|----------|------|
| Create/Edit Agent 頁面 ~80% 重複 | 1,973 行 | 抽取 `AgentForm` 共用元件，差異透過 props 控制 |
| Create/Edit Workflow 頁面 ~80% 重複 | 1,927 行 | 抽取 `WorkflowForm` 共用元件 |
| 2 個 ApprovalDialog 元件不同簽名 | 627 行 | 統一為單一 ApprovalDialog，功能合併 |
| UI barrel export 不完整 | 18 個元件僅 3 個從 index 匯出 | 統一 barrel export 模式 |

**預估可節省行數**：透過消除重複，可減少 ~2,500 行（~5% of total）

### 1.4 Prop Drilling 問題

**整體評估：低風險**

專案正確採用 Zustand 進行全域狀態管理，React Query 管理伺服器狀態，大幅降低了 prop drilling 的可能性。

**觀察到的模式**：
- `UnifiedChat.tsx` 作為協調層，將 hook 返回值透過 props 傳遞給子元件 — 這是合理的模式，因為 hook 需要在頁面層級被呼叫
- `agent-swarm/` 元件使用 `swarmStore` (Zustand) 避免深層傳遞
- `useSharedState` hook (505L) 提供跨元件狀態共享機制

**潛在改善**：`UnifiedChat.tsx` 傳遞過多 props 給 `ChatArea`, `ChatInput` 等子元件，可考慮將部分狀態提升到 `unifiedChatStore` 或建立 Context Provider。

---

## 2. 狀態管理分析

### 2.1 Zustand Store 清單與職責

| Store | 位置 | 行數 | 中介軟體 | 持久化 | 職責 |
|-------|------|------|----------|--------|------|
| `useAuthStore` | `store/authStore.ts` | 322 | `persist` | localStorage (`ipa-auth-storage`) | 認證 token、使用者資訊、登入/登出/刷新 |
| `useUnifiedChatStore` | `stores/unifiedChatStore.ts` | 508 | `devtools`, `persist` | localStorage (100 條訊息限制) | 聊天模式、訊息、工作流、工具呼叫、審批、檢查點、指標、連線狀態 |
| `useSwarmStore` | `stores/swarmStore.ts` | 444 | `immer`, `devtools` | 無 | Swarm 狀態、Worker 管理、抽屜 UI 狀態 |

### 2.2 store/ vs stores/ 重複問題 — HIGH

```
frontend/src/
├── store/              ← 只有 authStore.ts（歷史遺留？）
│   └── authStore.ts
└── stores/             ← 功能性 stores
    ├── swarmStore.ts
    ├── unifiedChatStore.ts
    └── __tests__/
```

**問題**：兩個目錄的分離沒有明確的架構理由。`store/` 是 Sprint 71 建立的，`stores/` 是後續 Sprint 建立的。這造成：
1. 新開發者混淆：store 該放哪個目錄？
2. Import 路徑不一致：`@/store/authStore` vs `@/stores/unifiedChatStore`
3. 違反單一位置原則

**建議**：統一至 `stores/` 目錄，將 `authStore.ts` 遷移過去，更新所有 import。

### 2.3 狀態共享模式

**雙軌策略（正確）**：

```
Client State (Zustand)          Server State (React Query)
┌─────────────────────┐         ┌─────────────────────────┐
│ authStore            │         │ useQuery(['agents'])     │
│ unifiedChatStore     │         │ useQuery(['workflows'])  │
│ swarmStore           │         │ useMutation(createAgent) │
│ (UI 狀態 + 會話狀態)  │         │ (CRUD 操作 + 快取)       │
└─────────────────────┘         └─────────────────────────┘
```

**React Query 使用統計**：
- `useQuery` / `useMutation` / `useQueryClient` 共 61 處引用
- `staleTime: 5 分鐘`，合理的預設快取策略
- `refetchOnWindowFocus: false`，適合企業應用

**unifiedChatStore 過大問題**：
508 行的 store 管理了 15+ 個狀態欄位，建議按功能域拆分：

```
unifiedChatStore.ts (508L) →
├── chatMessagesSlice.ts    — 訊息管理
├── chatModeSlice.ts        — 模式切換
├── chatApprovalSlice.ts    — 審批狀態
├── chatMetricsSlice.ts     — 指標追蹤
└── chatConnectionSlice.ts  — 連線狀態
```

### 2.4 Server State 管理

**React Query 配置評估**：

```typescript
// main.tsx — 全域配置
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 分鐘 ✅
      retry: 1,                   // 合理 ✅
      refetchOnWindowFocus: false, // 企業場景適當 ✅
    },
  },
});
```

**缺失的模式**：
- 無 `suspense` 模式整合（可搭配 React.Suspense 改善 UX）
- 無 `placeholderData` / `keepPreviousData` 策略
- 無全域 error handler（`queryClient.setDefaultOptions({ mutations: { onError } })`）

---

## 3. TypeScript 品質

### 3.1 型別覆蓋率 — EXCELLENT

| 指標 | 數值 | 評級 |
|------|------|------|
| `any` 型別使用 | **1** (`as any` 在 `ApiError`) | 優異 |
| 類型定義檔案 | 4 個專用 `.ts` 檔案 + 內嵌型別 | 良好 |
| Props Interface 覆蓋 | ~100%（所有元件皆有 Props 介面） | 優異 |
| 嚴格模式 | `tsconfig.json` strict: true | 優異 |

**唯一的 `as any` 出處**：
```typescript
// api/client.ts:38
public details?: unknown  // 正確使用 unknown 而非 any ✅
```

API Client 中 `details` 欄位使用 `unknown`（非 `any`），顯示良好的類型紀律。

### 3.2 型別設計品質

**良好模式**：
- `interface` 用於物件形狀（`Agent`, `WorkflowStep`, `ChatMessage`）
- `type` 用於聯合型別（`ExecutionMode = 'chat' | 'workflow'`）
- 所有 Hook 返回值都有明確的 interface（`UseUnifiedChatReturn`）
- 型別匯出與實作匯出分離

**可改善之處**：
- `types/ag-ui.ts` (422L) 和 `types/unified-chat.ts` (505L) 檔案較大，可按功能細分
- 部分 `Record<string, unknown>` 可替換為更精確的型別
- Swarm 類型定義在 `components/unified-chat/agent-swarm/types/` 而非頂層 `types/`，造成層次不一致

---

## 4. 效能分析

### 4.1 Re-render 風險 — MEDIUM

**Memoization 統計**：

| 技術 | 使用次數 | 評估 |
|------|----------|------|
| `useCallback` + `useMemo` | 460 次 | 良好，積極使用 |
| `React.memo` | 6 次（僅 workflow-editor） | 嚴重不足 |
| `React.lazy` | **0 次** | 缺失 |

**高風險 Re-render 場景**：

1. **UnifiedChat.tsx** — 899 行頁面元件，內含 15+ 個 state/hook 呼叫。任何狀態變化都會觸發整個元件樹 re-render
2. **MessageList** — 訊息列表無虛擬化，大量訊息時效能下降
3. **OrchestrationPanel (508L)** — 複雜面板無 memo 保護
4. **agent-swarm/ 的 15 個元件** — 即時更新場景（SSE 推送）下 re-render 頻繁

**建議**：
- 對 `WorkerCard`, `ToolCallItem`, `MessageBubble` 等列表項目元件加上 `React.memo`
- 對 `OrchestrationPanel`, `ChatArea` 等大型子元件加上 `React.memo`
- 考慮 `MessageList` 使用 `react-window` 或 `@tanstack/react-virtual` 虛擬化

### 4.2 Code Splitting 狀況 — CRITICAL

**現狀：完全沒有 Code Splitting。**

```typescript
// App.tsx — 所有 26+ 頁面同步 import
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { WorkflowsPage } from '@/pages/workflows/WorkflowsPage';
import { CreateAgentPage } from '@/pages/agents/CreateAgentPage';
// ... 全部同步載入
```

**零 `React.lazy` / `Suspense` 使用**意味著：
- 首次載入下載全部 JS bundle
- 使用者訪問 `/dashboard` 也載入了 `SwarmTestPage`, `AGUITestPanel`, `TraceDetail` 等不相關頁面的程式碼
- 對行動裝置和低頻寬環境影響尤其明顯

**建議分割策略**：

```typescript
// App.tsx — 推薦的 lazy loading 模式
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const CreateAgentPage = lazy(() => import('@/pages/agents/CreateAgentPage'));
const SwarmTestPage = lazy(() => import('@/pages/SwarmTestPage'));
const DevUILayout = lazy(() => import('@/pages/DevUI/Layout'));
const AGUIDemoPage = lazy(() => import('@/pages/ag-ui/AGUIDemoPage'));
const WorkflowEditorPage = lazy(() => import('@/pages/workflows/WorkflowEditorPage'));

// 搭配 Suspense fallback
<Suspense fallback={<LoadingSpinner />}>
  <Routes>...</Routes>
</Suspense>
```

### 4.3 Bundle 大小評估

**vite.config.ts 手動分塊配置**：

```typescript
manualChunks: {
  vendor: ['react', 'react-dom', 'react-router-dom'],  // ~140KB gzipped
  charts: ['recharts'],                                  // ~80KB gzipped
  query: ['@tanstack/react-query'],                      // ~15KB gzipped
}
```

**缺失的分塊**：

| 依賴 | 預估大小 (gzipped) | 建議 |
|------|---------------------|------|
| `@xyflow/react` + `dagre` | ~120KB | 應單獨分塊（僅 workflow editor 使用） |
| `immer` | ~5KB | 小，可留在主 bundle |
| `lucide-react` | ~10-30KB (依 tree shaking) | 確認 tree shaking 正常運作 |
| Radix UI (10 個套件) | ~30KB | 可歸入 ui-vendor 塊 |

**預估首次載入改善空間**：透過 lazy loading + 額外分塊，可減少首次載入 ~200-250KB gzipped。

---

## 5. API 整合層分析

### 5.1 API Client 設計 — GOOD

```
api/
├── client.ts          — 173L，統一 Fetch 封裝（乾淨）
├── devtools.ts        — DevTools 專用 API
└── endpoints/
    ├── index.ts       — Barrel export
    ├── ag-ui.ts       — AG-UI Protocol endpoints
    ├── files.ts       — 388L，檔案管理（含上傳/下載）
    └── orchestration.ts — 編排 API
```

**優點**：
- 統一的 `fetchApi<T>()` 泛型封裝，型別安全
- 自動 Auth Token 注入（從 Zustand store 讀取）
- Guest User Header (`X-Guest-Id`) 支援
- 401 自動登出 + 重導向
- `ApiError` 類別提供結構化錯誤處理

**問題**：

| 問題 | 嚴重度 | 詳述 |
|------|--------|------|
| authStore 中有獨立的 `fetch` 呼叫 | MEDIUM | `apiLogin`, `apiRegister`, `apiGetMe`, `apiRefreshToken` 4 個函數直接使用 `fetch()`，繞過 `api/client.ts` 封裝。理由可理解（避免循環依賴），但造成錯誤處理模式不一致 |
| 無請求取消機制 | MEDIUM | 缺少 `AbortController` 整合，快速切換頁面時可能有 race condition |
| 無 retry 邏輯 | LOW | API client 層無自動重試（React Query 有 `retry: 1` 但僅限 query） |
| 204 回應強制轉型 | LOW | `return {} as T` 在 204 回應時可能導致型別不匹配 |

### 5.2 錯誤處理一致性 — MEDIUM

**兩種錯誤處理模式並存**：

1. **API Client 層**：`ApiError` 類別 + HTTP 狀態碼
2. **頁面/元件層**：`try/catch` → `generateMock*()` 靜默降級

**嚴重問題（V8 Issue H-08）**：10+ 頁面在 API 失敗時靜默降級為 mock 資料，使用者無法區分真實資料與假資料。

**影響頁面**：Dashboard, AgentsPage, WorkflowsPage, ApprovalsPage, AuditPage, TemplatesPage

### 5.3 Loading/Error 狀態

- React Query 提供 `isLoading`, `error` 狀態 — 正確使用
- 共用 `LoadingSpinner` 和 `EmptyState` 元件存在
- SSE 串流有 `ConnectionStatus` 元件顯示連線狀態
- **缺失**：無全域 error toast/notification 系統

---

## 6. 可訪問性 (Accessibility) 分析

### 6.1 ARIA 屬性使用 — INSUFFICIENT

| 指標 | 數值 | 評估 |
|------|------|------|
| `aria-*` / `role=` 屬性 | 70 處 | 不足（153 元件中僅部分覆蓋） |
| Shadcn UI 內建 ARIA | 18 個基礎元件 | 良好（Radix UI 提供） |
| 自定義元件 ARIA | ~52 處 | 覆蓋率約 34% |

**V8 Issue M-20 確認**：Swarm 元件（`WorkerCard`, `ToolCallItem`）缺少明確的 `aria-label`。

**缺失的關鍵可訪問性功能**：
1. 無鍵盤導航測試記錄
2. 聊天介面缺少 `aria-live` 區域（新訊息不會被螢幕閱讀器自動通知）
3. 表單頁面（Create/Edit Agent/Workflow）缺少表單驗證的 `aria-invalid` 和 `aria-describedby`
4. DevUI 圖表（Recharts）缺少替代文字

### 6.2 鍵盤導航

- Shadcn UI (Radix) 元件原生支援鍵盤導航
- 自定義元件的鍵盤支援未系統性驗證
- 聊天輸入框預期支援 Enter 發送，但快捷鍵文件不明確

---

## 7. 目錄結構與程式碼衛生

### 7.1 結構評估

**良好**：
- 頁面、元件、hooks、store、types 分離清晰
- `components/unified-chat/` 內部組織良好（含 `agent-swarm/` 子目錄和 `renderers/`）
- `api/endpoints/` 按功能域分離

**問題**：

| 問題 | 嚴重度 | 詳述 |
|------|--------|------|
| `store/` vs `stores/` 雙目錄 | HIGH | 見 2.2 節 |
| `dialog.tsx` 小寫命名 | LOW | V8 Issue L-02：與其他 PascalCase UI 元件不一致 |
| `ui/index.ts` 僅匯出 3/18 元件 | LOW | V8 Issue L-01：Barrel export 不完整 |
| Swarm types 在元件目錄而非 `types/` | MEDIUM | `components/unified-chat/agent-swarm/types/` 違反集中型別管理原則 |
| 2 個 "Coming Soon" 佔位頁面 | LOW | V8 Issue L-07：`LiveMonitor.tsx`, `Settings.tsx` |

### 7.2 Dead Code / 未使用的程式碼

| 項目 | 詳述 |
|------|------|
| `useSwarmMock.ts` (623L) | 開發用 mock hook，生產環境不需要 |
| `pairedEvent` prop 被忽略 | V8 Issue L-03：DevUI 面板接收但不使用 |
| Header 搜尋欄 | V8 Issue L-04：純視覺元素，無功能 |
| 通知鈴鐺紅點 | V8 Issue L-05：永遠顯示，未接真實通知系統 |
| "Use Template" 按鈕 | V8 Issue L-08：無 click handler |

### 7.3 Console 語句 — MEDIUM

| 類型 | 數量 | 建議 |
|------|------|------|
| `console.log` | **49** | 應移除或替換為可配置 logger |
| `console.warn` | ~30 | 部分合理（debug-gated），部分應移除 |
| `console.error` | ~29 | 可保留，建議配合錯誤追蹤服務 |
| **總計** | **~108** | 需要清理 |

---

## 8. 與 V8 Issue Registry 的交叉對照

以下為 V8 Issue Registry 中所有前端相關問題的對應分析：

| V8 Issue | 嚴重度 | 本報告確認 | 額外發現 |
|----------|--------|------------|----------|
| **H-08** 10 頁面靜默 mock 降級 | HIGH | 確認 | 建議加入 `<MockDataBanner>` 元件 |
| **H-11** Chat 只存 localStorage | HIGH | 確認 | 跨裝置/瀏覽器會遺失歷史 |
| **H-15** Error Boundary 不足 | HIGH | 確認 | 僅 ChatArea 有 ErrorBoundary，17 處引用但覆蓋不完整 |
| **M-12** Create/Edit 80% 重複 | MEDIUM | 確認 | 4 個檔案共 3,900 行可壓縮至 ~1,500 行 |
| **M-13** 55+ console 語句 | MEDIUM | 確認（實測 108 處含 warn/error） | 建議引入 `loglevel` 或自定義 logger |
| **M-14** AG-UI demo 用模擬資料 | MEDIUM | 確認 | 6/7 demo 用假資料 |
| **M-15** 重複 ApprovalDialog | MEDIUM | 確認 | unified-chat (383L) vs ag-ui (244L) |
| **M-16** 工具/模型列表寫死 | MEDIUM | 確認 | CreateAgentPage 中硬編碼 |
| **M-17** Token 估算不準 | MEDIUM | 確認 | ~3 chars/token 對中文不適用 |
| **M-20** Swarm 缺 aria-labels | MEDIUM | 確認 | WorkerCard, ToolCallItem |
| **L-01** UI barrel export 不全 | LOW | 確認 | 3/18 元件匯出 |
| **L-02** dialog.tsx 小寫 | LOW | 確認 | 唯一小寫命名檔案 |
| **L-03** pairedEvent 未使用 | LOW | 確認 | |
| **L-04** 搜尋欄無功能 | LOW | 確認 | |
| **L-05** 通知紅點假的 | LOW | 確認 | |
| **L-07** 2 個 Coming Soon 頁面 | LOW | 確認 | |
| **L-08** Template 按鈕無功能 | LOW | 確認 | |
| **L-16** 2 個 TODO 註解 | LOW | 確認 | |

**本報告新發現（V8 未涵蓋）**：

| 新 Issue | 嚴重度 | 詳述 |
|----------|--------|------|
| **NEW-F01** 零 Code Splitting | CRITICAL | 無 React.lazy，全部同步載入，影響首次載入效能 |
| **NEW-F02** React.memo 幾乎未使用 | HIGH | 僅 6 處（全在 workflow-editor），其他 100+ 元件無 memo |
| **NEW-F03** store/stores 雙目錄 | HIGH | 架構不一致，造成開發者混淆 |
| **NEW-F04** 無請求取消機制 | MEDIUM | API client 缺 AbortController，頁面快速切換時有 race condition |
| **NEW-F05** 無虛擬化列表 | MEDIUM | MessageList 大量訊息時效能問題 |
| **NEW-F06** authStore 繞過 API client | MEDIUM | 4 個函數直接 fetch，錯誤處理不一致 |
| **NEW-F07** 缺少 aria-live 區域 | MEDIUM | 聊天新訊息不通知螢幕閱讀器 |

---

## 9. 架構改進建議 — 優先序路線圖

### Phase A: 立即修復（1-2 Sprints）

| 優先 | 動作 | 影響 | 預估工時 |
|------|------|------|----------|
| 1 | 實作 React.lazy Code Splitting（所有路由） | 首次載入減少 ~200KB gzipped | 3 pts |
| 2 | 統一 `store/` → `stores/` 目錄 | 架構一致性 | 2 pts |
| 3 | 合併重複 ApprovalDialog | 消除 627L 重複 | 3 pts |
| 4 | 清理 console.log（49 處） | 程式碼衛生 | 2 pts |
| 5 | 修復 `dialog.tsx` → `Dialog.tsx` 命名 | 一致性 | 1 pt |

### Phase B: 短期改善（3-5 Sprints）

| 優先 | 動作 | 影響 | 預估工時 |
|------|------|------|----------|
| 6 | 拆分 `useUnifiedChat.ts` (1,313L → 6 hooks) | 可維護性、可測試性 | 8 pts |
| 7 | 抽取 `AgentForm` / `WorkflowForm` 共用元件 | 消除 ~2,400L 重複 | 8 pts |
| 8 | 加入 `<MockDataBanner>` 元件 | 使用者可區分真實/假資料 | 3 pts |
| 9 | Error Boundary 全頁面覆蓋 | 錯誤隔離 | 5 pts |
| 10 | 加入 `@xyflow/react` 獨立 bundle chunk | Bundle 大小最佳化 | 2 pts |

### Phase C: 中期最佳化（5-10 Sprints）

| 優先 | 動作 | 影響 | 預估工時 |
|------|------|------|----------|
| 11 | MessageList 虛擬化 | 大量訊息效能 | 5 pts |
| 12 | 關鍵元件加入 React.memo | Re-render 最佳化 | 5 pts |
| 13 | 聊天介面 aria-live + 表單 ARIA 增強 | WCAG 2.1 AA 合規 | 5 pts |
| 14 | 建立 Logger 工具替代 console | 可觀測性 | 3 pts |
| 15 | API client 加入 AbortController | 取消請求，避免 race condition | 3 pts |
| 16 | 完善 UI barrel exports | 一致的匯入模式 | 2 pts |
| 17 | Swarm types 遷移至 `types/` | 型別組織一致性 | 2 pts |

---

## 10. 架構健康度評分卡

| 維度 | 分數 (1-10) | 說明 |
|------|-------------|------|
| **TypeScript 品質** | **9.5/10** | 幾乎零 any，嚴格模式，完整 Props 介面 |
| **元件架構** | **6.5/10** | 層次清晰但有大型元件和重複問題 |
| **狀態管理** | **7.5/10** | Zustand + React Query 策略正確，但有目錄分裂和 store 過大 |
| **效能** | **5.0/10** | 無 Code Splitting 是重大缺陷，memo 使用不足 |
| **API 整合** | **7.5/10** | Client 設計良好，但有直接 fetch 和缺少取消機制 |
| **可訪問性** | **5.0/10** | Radix UI 提供基礎，但自定義元件覆蓋不足 |
| **程式碼衛生** | **6.5/10** | console 過多，命名不一致，佔位功能殘留 |
| **設計系統** | **8.0/10** | Tailwind + Shadcn 一致性好 |
| **整體** | **6.9/10** | 中上水準，有明確的改善路線 |

---

*報告結束。本分析基於對 200 個原始碼檔案的結構掃描、關鍵檔案深度閱讀、以及 V8 Issue Registry 交叉驗證。*
