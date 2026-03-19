# Sprint 140 Checklist: Knowledge 管理 + Memory 檢視 + 導航

## Sprint 目標

| 項目 | 值 |
|------|-----|
| **總點數** | 8 點 |
| **狀態** | 📋 計劃中 |

---

## 開發任務

### S140-1: Knowledge 管理頁面 (3 SP)
- [ ] 新增 `frontend/src/api/endpoints/knowledge.ts`
- [ ] 實作 `uploadDocument(file, metadata)` — POST /knowledge/documents（multipart/form-data）
- [ ] 實作 `searchKnowledge(query, options)` — POST /knowledge/search
- [ ] 實作 `getDocuments(filters)` — GET /knowledge/documents
- [ ] 實作 `deleteDocument(id)` — DELETE /knowledge/documents/{id}
- [ ] 實作 `getSkills()` — GET /knowledge/skills
- [ ] 實作 `getKnowledgeStatus()` — GET /knowledge/status
- [ ] 新增 `frontend/src/hooks/useKnowledge.ts`
- [ ] 實作 `useKnowledgeSearch(query)` — 語義搜索 hook
- [ ] 實作 `useDocuments(filters)` — 文檔列表查詢 hook
- [ ] 實作 `useUploadDocument()` — 文檔上傳 mutation hook
- [ ] 實作 `useDeleteDocument()` — 文檔刪除 mutation hook
- [ ] 實作 `useSkills()` — 技能列表查詢 hook
- [ ] 實作 `useKnowledgeStatus()` — 服務狀態查詢 hook
- [ ] 新增 `frontend/src/pages/knowledge/KnowledgePage.tsx`
- [ ] 實作 Tab 導航：文檔管理 | 語義搜索 | 技能列表
- [ ] 實作文檔上傳區（拖拽上傳 + 點擊上傳，支援 PDF/TXT/MD/DOCX）
- [ ] 實作已上傳文檔列表（名稱、大小、上傳時間、狀態）
- [ ] 實作語義搜索（搜索輸入框 + 結果列表含相似度分數）
- [ ] 實作技能列表（名稱、描述、狀態）
- [ ] 實作服務狀態指示器：Qdrant 不可用時顯示警告
- [ ] 使用 Shadcn UI Tabs + Card + Table + Input + Button 組件

### S140-2: Memory 檢視頁面 (2 SP)
- [ ] 新增 `frontend/src/api/endpoints/memory.ts`
- [ ] 實作 `searchMemories(query, userId)` — POST /memory/search
- [ ] 實作 `getUserMemories(userId, options)` — GET /memory/users/{userId}
- [ ] 實作 `getMemoryStats()` — GET /memory/stats
- [ ] 實作 `deleteMemory(id)` — DELETE /memory/{id}
- [ ] 新增 `frontend/src/hooks/useMemory.ts`
- [ ] 實作 `useMemorySearch(query, userId)` — 記憶搜索 hook
- [ ] 實作 `useUserMemories(userId)` — 使用者記憶列表 hook
- [ ] 實作 `useMemoryStats()` — 記憶統計 hook
- [ ] 實作 `useDeleteMemory()` — 記憶刪除 mutation hook
- [ ] 新增 `frontend/src/pages/memory/MemoryPage.tsx`
- [ ] 實作記憶搜索區塊：搜索輸入框 + User ID 篩選
- [ ] 實作搜索結果列表（記憶內容、建立時間、相關度分數）
- [ ] 實作使用者記憶列表（按時間排序，可展開查看完整內容）
- [ ] 實作記憶統計儀表板（總記憶數、使用者數、最近更新時間）
- [ ] 實作刪除記憶操作
- [ ] 使用 Shadcn UI Card + Input + Table + Badge 組件

### S140-3: MemoryHint 內聯組件 (1 SP)
- [ ] 新增 `frontend/src/components/unified-chat/MemoryHint.tsx`
- [ ] 實作 Props interface: `{ memories: MemoryItem[]; isVisible: boolean }`
- [ ] 實作顯示位置：Chat 輸入框上方
- [ ] 實作顯示格式：「找到 {count} 條相關記憶」+ 可展開列表
- [ ] 每條記憶顯示：內容摘要（前 100 字）、建立時間
- [ ] 實作可展開/摺疊（預設摺疊）
- [ ] 實作可關閉（點擊 X 隱藏提示）
- [ ] 實作淡入動畫效果
- [ ] 使用 Shadcn UI Alert + Collapsible + Button 組件

### S140-4: 最終路由 + 導航 + 整合 (2 SP)
- [ ] 修改 `frontend/src/App.tsx` — 新增路由 `/knowledge` → KnowledgePage
- [ ] 修改 `frontend/src/App.tsx` — 新增路由 `/memory` → MemoryPage
- [ ] Lazy import 新增頁面組件
- [ ] 驗證所有 Phase 40 路由正確運作（/sessions, /tasks, /knowledge, /memory）
- [ ] 修改 `frontend/src/components/layout/Sidebar.tsx` — 新增「知識庫」導航項目
- [ ] 設定知識庫導航圖標（BookOpen 或 Database icon），路由 `/knowledge`
- [ ] 修改 `frontend/src/components/layout/Sidebar.tsx` — 新增「記憶系統」導航項目
- [ ] 設定記憶系統導航圖標（Brain 或 Lightbulb icon），路由 `/memory`
- [ ] 確認完整 Sidebar 導航順序（11 項：Dashboard → Chat → Sessions → 任務 → 知識庫 → 記憶 → 工作流 → Agents → 審批 → 審計 → DevUI）

## 驗證標準

- [ ] Knowledge API client 能正確呼叫所有 /knowledge 端點
- [ ] 知識庫頁面能上傳文檔（拖拽 + 點擊）
- [ ] 知識庫頁面能進行語義搜索並顯示結果
- [ ] 知識庫頁面 Qdrant 不可用時顯示警告提示
- [ ] Memory API client 能正確呼叫所有 /memory 端點
- [ ] 記憶頁面能搜索和瀏覽使用者記憶
- [ ] MemoryHint 在 Chat 輸入框上方正確顯示記憶提示
- [ ] MemoryHint 可展開查看記憶摘要、可關閉
- [ ] Sidebar 包含知識庫和記憶系統導航入口
- [ ] 所有 Phase 40 路由正確運作（/sessions, /tasks, /knowledge, /memory）
- [ ] 所有新增組件使用 TypeScript + Shadcn UI
- [ ] 所有新增程式碼通過 ESLint 檢查
- [ ] npm run build 無錯誤

## 相關連結

- [Phase 40 計劃](./README.md)
- [Sprint 140 Plan](./sprint-140-plan.md)
- [Sprint 138 Plan](./sprint-138-plan.md)

---

**Sprint 狀態**: 📋 計劃中
**Story Points**: 8
