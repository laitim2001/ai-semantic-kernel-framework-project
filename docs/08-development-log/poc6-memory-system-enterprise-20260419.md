❯  c:\Users\Chris\Downloads\ai-semantic-kernel-framework-project\docs\09-git-worktree-working-folder\knowledge-base-enterprise                   現在你可以先檢查和分析一下這文件夾內的內容, 這是之前的一些研究和分析, 請在檢查完之後提出你的意見 (其中是包含了關於memory的,            所以你可以選擇性地理解)                                                                                                                  
                                                                                                                                           
  Searched for 1 pattern, read 1 file (ctrl+o to expand)                                                                                   
                                                                                                                                           
  Read 2 files (ctrl+o to expand)    
                                                                                                                                           
● 文件集分析與意見
                                                                                                                                           
  整體評估                                                                                                                                 
                                                                                                                                             這是一份 2026-04 份量紮實的 8 份研究系列（Doc 00–08），由 Chris Lai（RAPO / IPA Platform Architect）整理。雖然命名為                       knowledge-base-enterprise，但 Doc 02 完整覆蓋 Agent Memory，與 RAG/GraphRAG 研究並行。質素：9/10（含最新 paper、SOTA                     
  benchmark、build-vs-buy、9-month roadmap、cost estimate）。                                                                                                                                                                                                                         
  與 research/memory-system-enterprise worktree 的關係                                                                                     
                                                                                                                                             ┌──────────────────────┬────────────────────────────────────────────────────────────────────────────────────────┐                          │         項目         │                                          現狀                                          │                        
  ├──────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ 可直接複用           │ Doc 02（Agent Memory 深入）+ Doc 08 對 V8 mem0 的 gap analysis                         │
  ├──────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ 知識庫相關（可忽略） │ Doc 03–07（RAG/GraphRAG/Ontology/Ingestion）                                           │
  ├──────────────────────┼────────────────────────────────────────────────────────────────────────────────────────┤
  │ 交集（需保留）       │ Doc 06 Graphiti — 同時解決 memory bitemporal + ontology，是 memory worktree 的關鍵選項 │
  └──────────────────────┴────────────────────────────────────────────────────────────────────────────────────────┘

  核心洞察（Memory 專屬）

  1. V8 現狀：mem0 三層（maturity L3）— 確實過於簡化
  2. SOTA 方向：MIRIX 的 6-component schema（Core / Episodic / Semantic / Procedural / Working / Resource / Knowledge Vault）已是業界標準  
  3. 最大槓桿：Active Retrieval（MIRIX-style topic-first query expansion）— 解決「save 過但 recall 唔到」經典問題
  4. Enterprise 殺手鐧：Bitemporal（event time vs ingestion time）— audit/compliance 天然 fit
  5. 已建議的分段 roadmap：
    - 短期（1–2 月）：Active Retrieval + org_scope/tenant dimension
    - 中期（3–6 月）：6-component schema + Graphiti 整合
    - 長期（6–12 月）：Memory evolution + reflection（A-MEM pattern）

  我的意見與補充

  優點（該研究已做得好的）:
  - 理論框架完整（POMDP write-manage-read loop、記憶演化三階段）
  - 主流系統對比詳盡（LongMemEval 成績、trade-off）
  - 決策樹清晰（選型不再靠感覺）

  該研究未充分覆蓋的 gap（memory worktree 應補）:
  1. Multi-tenant 隔離策略 — Doc 只提到「加 org_scope」，但未深入 row-level security、tenant-scoped embedding namespace 等企業必要細節     
  2. Memory 與 Agent Expert Registry（Phase 46）的整合 — 每個 expert agent 應有專屬 memory scope？共用？策略未討論
  3. Memory 與現有 Orchestrator（Phase 45 3-route dispatch）的交互 — Active Retrieval 應在 pipeline 哪一步執行？
  4. Cost-aware memory tiering — 哪些記憶進 RAM（core context）、哪些冷儲存、何時 compaction 的具體 policy
  5. HITL approval for memory write — 企業場景哪些 memory 寫入需人工審核（例如 policy、compliance fact）

  建議 memory worktree 的切入路徑:
  1. 複製 Doc 02 + Doc 08 到 memory worktree（已可直接引用）
  2. 第一步研究：盤點 V9 現有 mem0 三層的 API/schema，對照 MIRIX 6-component 做 gap mapping
  3. 第二步討論：決定是走 Graphiti 路線（與 knowledge worktree 共享基礎設施）還是獨立演進 mem0
  4. 第三步 PoC：Active Retrieval 是最小可驗證 patch（現有 pipeline 加一層 topic generation）

  請問您想從哪一步開始？

==================================================================

==================================================================
● V9 記憶架構 Gap Analysis — 對照 Doc 08 建議                                                                                              
                          
  一、V9 現狀快照（2026-03-30 + Phase 45-47 更新）                                                                                         
                                                                                                                                             ┌───────────────────┬────────────────────────────────────────────────────┬──────────────────────────────┐
  │       維度        │                      V9 現狀                       │           整體評分           │                                  ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤                                  │ L1 Working Memory │ Redis，30 分 TTL                                   │ ✅ 良好                      │                                
  ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤                                  │ L2 Session Memory │ 設計 PostgreSQL，實際 Redis+長 TTL（未按設計落地） │ ⚠️ 需修正                    │                                   ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤                                
  │ L3 Long-Term      │ mem0 + Qdrant（永久）                              │ ✅ 良好（有 async 阻塞問題） │
  ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤
  │ Pipeline 整合     │ Step 1 read + Step 8 write（Phase 45-47 新增）     │ ✅ 結構化                    │
  ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤
  │ Context Budget    │ context_budget.py 明確 token 分配                  │ ✅ 已超越 Doc 08 預期        │
  ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤
  │ Consolidation     │ consolidation.py episodic→semantic                 │ 🟡 雛形，未完整              │
  ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤
  │ InMemory 揮發風險 │ 12 元件（17%），2 HIGH / 5+ MEDIUM                 │ 🔴 P0/P1 遷移未完成          │
  ├───────────────────┼────────────────────────────────────────────────────┼──────────────────────────────┤
  │ 整體評分          │ B+（Phase 47 後由 B 升級）                         │ —                            │
  └───────────────────┴────────────────────────────────────────────────────┴──────────────────────────────┘

  二、V9 vs Doc 08 短期建議（1-2 月）

  ┌─────────────────────────────────┬───────────────────────────────────────────────────────────┬─────────────────────────────┬────────┐   
  │           Doc 08 建議           │                        V9 實際狀態                        │             Gap             │ 優先級 │   
  ├─────────────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────┼────────┤   
  │ Active Retrieval（MIRIX         │ V9 用 importance score 路由（>=0.8 → L3），無 topic       │ ✅ 真實 Gap — 核心 quick    │ 🔴 P0  │   
  │ topic-first）                   │ generation                                                │ win 未落地                  │        │   
  ├─────────────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────┼────────┤   
  │ 加 org_scope / tenant dimension │ V9 架構文件完全無 tenant 欄位；MemoryType enum            │ ✅ 真實 Gap — 企業必要      │ 🔴 P0  │   
  │                                 │ 只有功能分類，無組織隔離                                  │                             │        │   
  └─────────────────────────────────┴───────────────────────────────────────────────────────────┴─────────────────────────────┴────────┘   

  三、V9 vs Doc 08 中期建議（3-6 月）

  Doc 08 建議: 升級 6-component schema（Core / Episodic / Semantic / Procedural / Working / Resource / Knowledge Vault）
  V9 實際狀態: V9 有 MemoryType 6 值（EVENT_RESOLUTION / BEST_PRACTICE / SYSTEM_KNOWLEDGE / USER_PREFERENCE / FEEDBACK / CONVERSATION）—   
    數字剛好都是 6 但語義完全不同。V9 分類按「重要性 → 存哪層」，MIRIX 按「認知功能 → 如何 retrieve」
  Gap: ✅ 真實 Gap — 正交維度，需並存
  優先級: 🟡 P1
  ────────────────────────────────────────
  Doc 08 建議: Graphiti 整合（同時解決 bitemporal + KG + memory）
  V9 實際狀態: V9 無任何 bitemporal 支援；無 KG 層；checkpoint 有時戳但不支援 event-time vs ingestion-time 分離
  Gap: ✅ 真實 Gap — 企業 audit/compliance 殺手鐧未建
  優先級: 🟡 P1

  四、V9 vs Doc 08 長期建議（6-12 月）

  ┌───────────────────────────┬─────────────────────────────────────────────────────┬──────────────────────────────────────────────────┐   
  │        Doc 08 建議        │                     V9 實際狀態                     │                       Gap                        │   
  ├───────────────────────────┼─────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤   
  │ Memory evolution +        │ Phase 45-46 consolidation.py 已有 episodic→semantic │ 🟡 部分已動，需擴展成 full                       │   
  │ reflection loop（A-MEM）  │  雛形                                               │ reflection（retroactive link                     │   
  │                           │                                                     │ update、LLM-generated tags）                     │   
  ├───────────────────────────┼─────────────────────────────────────────────────────┼──────────────────────────────────────────────────┤   
  │ Procedural memory / skill │ V9 MemoryType 有 BEST_PRACTICE 但無 skill           │ ✅ 真實 Gap                                      │   
  │  compilation              │ 執行步驟結構化儲存；無 workflow/operation 步驟記憶  │                                                  │   
  └───────────────────────────┴─────────────────────────────────────────────────────┴──────────────────────────────────────────────────┘   

  五、Doc 08 未提、但 V9 發現的新問題

  ┌───────────────────────────────────────────────┬───────────────────────────────────────────────────────────────┬───────────────────┐    
  │                     項目                      │                            V9 發現                            │      優先級       │    
  ├───────────────────────────────────────────────┼───────────────────────────────────────────────────────────────┼───────────────────┤    
  │ InMemoryCheckpointStorage 揮發（HIGH 風險）   │ 進程重啟 = 工作流全毀；factory 已建好但未切換預設             │ 🔴 P0             │    
  ├───────────────────────────────────────────────┼───────────────────────────────────────────────────────────────┼───────────────────┤    
  │ InMemoryApprovalStorage 揮發（HIGH 風險）     │ 待審批 HITL 項目消失，安全鏈斷裂                              │ 🔴 P0             │    
  ├───────────────────────────────────────────────┼───────────────────────────────────────────────────────────────┼───────────────────┤    
  │ Mem0 同步阻塞 asyncio 事件迴圈                │ self._memory.add/search/get_all 同步呼叫在 async 方法中，未   │ 🟡 P1             │    
  │                                               │ asyncio.to_thread() 包裝                                      │                   │    
  ├───────────────────────────────────────────────┼───────────────────────────────────────────────────────────────┼───────────────────┤    
  │ 雙重後端介面不相容（Sprint 110 ABC vs Sprint  │ TTL 型別 timedelta vs int，6 High-Level Stores 無法用 7       │ 🟡                │    
  │ 119 Protocol）                                │ Domain Factories 的後端                                       │ P2（破壞性改動）  │    
  ├───────────────────────────────────────────────┼───────────────────────────────────────────────────────────────┼───────────────────┤    
  │ L2 Session Memory 未按設計落地                │ 設計 PostgreSQL，實際 Redis + longer TTL                      │ 🟡 P3             │    
  ├───────────────────────────────────────────────┼───────────────────────────────────────────────────────────────┼───────────────────┤    
  │ Checkpoint cleanup O(N)                       │ cleanup_expired() 逐一刪除                                    │ 🟢 P4             │    
  └───────────────────────────────────────────────┴───────────────────────────────────────────────────────────────┴───────────────────┘    

  六、Doc 08 低估 / V9 已超越的項目

  ┌───────────────────┬─────────────────────────────┬──────────────────────────────────────────────────────────────┐
  │       項目        │         Doc 08 假設         │                           V9 實際                            │
  ├───────────────────┼─────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Context budgeting │ 未提及（屬 Anthropic 原則） │ ✅ Phase 45-46 已落地 context_budget.py — 比 Doc 08 建議更前 │
  ├───────────────────┼─────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Pipeline 整合     │ 未設計明確讀寫時機          │ ✅ Step 1 read + Step 8 write 已結構化                       │
  ├───────────────────┼─────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ Consolidation     │ 算「長期建議」              │ ✅ Phase 45-46 雛形已存在 — 長期建議提前開始                 │
  └───────────────────┴─────────────────────────────┴──────────────────────────────────────────────────────────────┘

  七、整合後的 V9 Gap Analysis 總表

  ┌──────────────────────────────────────────────────────────────────┐
  │              V9 記憶系統企業化差距 — 優先順序                       │
  ├──────────────────────────────────────────────────────────────────┤
  │                                                                  │
  │  🔴 P0 (1-2 月，Blocker 級)                                       │
  │  ├── Active Retrieval (MIRIX topic-first)                        │
  │  ├── Multi-tenant / org_scope dimension                          │
  │  ├── InMemoryCheckpointStorage → Redis                           │
  │  └── InMemoryApprovalStorage → Postgres                          │
  │                                                                  │
  │  🟡 P1 (3-6 月，企業能力)                                          │
  │  ├── 6-component schema（正交於現有 tier）                         │
  │  ├── Graphiti 整合（bitemporal + KG + memory）                    │
  │  └── Mem0 async 包裝（asyncio.to_thread）                         │
  │                                                                  │
  │  🟢 P2-P4 (6-12 月，長期健康)                                      │
  │  ├── Full A-MEM reflection loop                                  │
  │  ├── Procedural memory / skill compilation                       │
  │  ├── Dual backend interface 統一                                  │
  │  ├── L2 Session Memory 真正遷去 PostgreSQL                        │
  │  └── Checkpoint cleanup batch delete                             │
  │                                                                  │
  └──────────────────────────────────────────────────────────────────┘

  八、關鍵觀察（V9 獨有）

  1. V9 已在結構上領先 Doc 08 兩個維度：Context Budget + Pipeline 整合。這兩項是 Anthropic context engineering 的核心原則，V9 已落地。     
  2. Doc 08 描述的「V8 現狀」與 V9 現狀差異有限：tier 結構未變，主要差異在 Phase 45-47 新增的三個模組（consolidation / context_budget /    
  extraction）。Doc 08 的 roadmap 大部分仍適用。
  3. V9 的 MemoryType 6 值是 tier-routing 分類，不等於 MIRIX 6-component。這是 Doc 08 未指出的細節 — 兩者應並存：
    - Tier axis（L1/L2/L3，TTL 決定）
    - Cognitive axis（Core/Episodic/Semantic/Procedural/Working/Resource/Knowledge Vault，功能決定）
  4. Doc 08 未涵蓋 V9 的 InMemory 揮發風險：這 2 個 HIGH 風險項目（Checkpoint + Approval）實際比 schema 升級更緊急，應插入 P0。

  ---
  第一步完成。Gap analysis 已產出，確認了：
  - Doc 08 roadmap 大部分仍適用
  - 需插入 P0：InMemory 遷移（Doc 08 未覆蓋）
  - 需修正認知：V9 已有 Context Budget + Pipeline 整合（Doc 08 視為未來）
  - 需並存：V9 tier axis + MIRIX cognitive axis 是正交關係

  準備好可以進入第 2 步 — 企業級設計討論（multi-tenant 隔離、Active Retrieval 落地方案）。請問您要繼續？

✻ Churned for 1m 19s      

※ recap: 研究 memory-system-enterprise worktree 的企業級記憶系統設計；剛完成 V9 現狀對照 Doc 08 建議的 gap                                   analysis。下一步是進入企業級設計討論，涵蓋 multi-tenant 隔離與 Active Retrieval 落地方案。 (disable recaps in /config)
==================================================================

==================================================================
● 企業級記憶系統設計討論                                                                                                                   
                                                                                                                                           
  前置定調                                                                                                                                                                                                                                                                            
  兩個主題有強耦合關係 — Active Retrieval 的 query 必須帶 tenant scope；tenant 隔離的效果取決於 retrieval 能否精確切割。因此兩者一起設計。                                                                                                                                            
  ---
  A — Multi-Tenant 隔離設計                                                                                                                                                                                                                                                             A.1 首要設計問題：Tenant 的粒度是什麼？                                                                                                  

  企業場景通常不只一層隔離，建議採用四層 scope model：

  Tenant Hierarchy（由外到內）
  ┌─────────────────────────────────────────┐
  │  Organization (org_id)                  │  ← 硬隔離（不同公司/BU）
  │  ┌───────────────────────────────────┐  │
  │  │  Workspace (workspace_id)         │  │  ← 團隊/部門
  │  │  ┌─────────────────────────────┐  │  │
  │  │  │  User (user_id)             │  │  │  ← 個人
  │  │  │  ┌───────────────────────┐  │  │  │
  │  │  │  │  Agent (agent_id)     │  │  │  │  ← 特定 expert
  │  │  │  └───────────────────────┘  │  │  │
  │  │  └─────────────────────────────┘  │  │
  │  └───────────────────────────────────┘  │
  └─────────────────────────────────────────┘

  關鍵決策：哪些 Memory Type 綁哪個 scope？

  ┌──────────────────┬────────────────────────┬──────────────────┐
  │    MemoryType    │       建議 scope       │       理由       │
  ├──────────────────┼────────────────────────┼──────────────────┤
  │ USER_PREFERENCE  │ user_id                │ 個人偏好         │
  ├──────────────────┼────────────────────────┼──────────────────┤
  │ CONVERSATION     │ user_id + agent_id     │ 對話歷史         │
  ├──────────────────┼────────────────────────┼──────────────────┤
  │ EVENT_RESOLUTION │ workspace_id           │ 團隊共享解決經驗 │
  ├──────────────────┼────────────────────────┼──────────────────┤
  │ BEST_PRACTICE    │ workspace_id 或 org_id │ 組織知識         │
  ├──────────────────┼────────────────────────┼──────────────────┤
  │ SYSTEM_KNOWLEDGE │ org_id                 │ 公司級           │
  ├──────────────────┼────────────────────────┼──────────────────┤
  │ FEEDBACK         │ user_id                │ 個人回饋         │
  └──────────────────┴────────────────────────┴──────────────────┘

  A.2 儲存實作選項（以 Qdrant / mem0 為例）

  Option: A1. Row-level filter
  實作方式: 單一 collection，每條 memory 帶 {org_id, workspace_id, user_id, agent_id} metadata，查詢時 filter
  優點: 改動最小、節省資源
  缺點: 洩漏風險靠 query 正確性、跨租戶查詢容易漏 filter
  適合: 同信任域（例：單一公司多部門）
  ────────────────────────────────────────
  Option: A2. Collection-per-org
  實作方式: 每 org 獨立 Qdrant collection，內部再 metadata filter
  優點: 強隔離邊界、可獨立 backup/GDPR 刪除
  缺點: Collection 數量爆炸、schema 演進麻煩
  適合: SaaS 多租戶
  ────────────────────────────────────────
  Option: A3. Instance-per-org
  實作方式: 每 org 獨立 mem0 + Qdrant instance
  優點: 完全隔離、合規最強
  缺點: 成本高、運維重
  適合: 金融/醫療
  ────────────────────────────────────────
  Option: A4. Tier-dependent hybrid
  實作方式: L1/L2 row-level（session 短暫）、L3 collection-per-org（長期）
  優點: 平衡成本與隔離
  缺點: 兩套機制、複雜
  適合: 推薦

  推薦 A4：L1（Redis key 加 org_id: prefix）+ L2（Postgres row filter）+ L3（Qdrant collection-per-org）。

  A.3 跨租戶共享（System Knowledge）

  需要明確的 promotion path：
  user-level memory → (推薦/HITL approve) → workspace-level
  workspace-level → (governance review) → org-level
  org-level → (platform ops) → system-level（跨 tenant 共享）

  這是 Doc 08 未覆蓋 的關鍵 — 記憶不只隔離，還要有受控的上升通道。

  A.4 V9 改動範圍（估算）

  ┌─────────────────────────────────────────┬──────────────────────────┬──────┐
  │                  改動                   │           檔案           │ 難度 │
  ├─────────────────────────────────────────┼──────────────────────────┼──────┤
  │ MemoryEntry 加 scope 欄位               │ memory/types.py          │ 低   │
  ├─────────────────────────────────────────┼──────────────────────────┼──────┤
  │ UnifiedMemoryManager query 強制帶 scope │ memory/unified_memory.py │ 中   │
  ├─────────────────────────────────────────┼──────────────────────────┼──────┤
  │ Qdrant collection 命名規則              │ memory/mem0_client.py    │ 中   │
  ├─────────────────────────────────────────┼──────────────────────────┼──────┤
  │ Middleware 注入 scope 從 JWT            │ api/middleware/          │ 低   │
  ├─────────────────────────────────────────┼──────────────────────────┼──────┤
  │ Promotion path UI/API                   │ 新增 endpoint            │ 高   │
  └─────────────────────────────────────────┴──────────────────────────┴──────┘

  ---
  B — Active Retrieval 落地設計

  B.1 現狀問題回顧

  V9 Step 1 (Memory Read) 目前做法（推測基於架構文件）：
  Step 1: 直接用 user query → embed → Qdrant search top-k

  缺陷：user 問「Twitter CEO 係邊個」時，若之前 save 的 memory 內容是「我買咗 Twitter，改名叫 X」，embedding similarity 可能對不上。       

  B.2 MIRIX-style Active Retrieval 核心

  Step 1a (NEW): Topic Generation
    ├─ Input:  current user query + recent dialog context
    ├─ LLM:    generate "current topic" (semantic intent)
    └─ Output: topic string（e.g., "Twitter/X company ownership current state"）

  Step 1b: Multi-Strategy Retrieval
    ├─ Embedding search: topic vector → L3
    ├─ Keyword search:   topic keywords → L2
    └─ Importance filter: recent + high-importance → L1

  Step 1c: Rerank + Budget
    ├─ Cohere Rerank 3 (Doc 08 推薦的 quick win)
    └─ Apply context_budget.py token cap

  B.3 落地選項

  ┌────────────────────────────┬────────────────────────────────────────────┬───────────────────────────┬────────────────┬────────────┐    
  │           Option           │                    設計                    │        成本/Query         │      延遲      │  實作難度  │    
  ├────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┼────────────────┼────────────┤    
  │ B1. Inline Topic           │ 在 Step 1 前加一個 mini-LLM call 生成      │ +1 small call (~$0.0001   │ +200-400ms     │ 低（1      │    
  │ Gen（單次額外 LLM call）   │ topic                                      │ with gpt-5-nano)          │                │ Sprint）   │    
  ├────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┼────────────────┼────────────┤    
  │ B2. HyDE Expansion         │ LLM 生成「假設答案」，embed 假設答案搜尋   │ +1 medium call            │ +400-800ms     │ 中         │    
  ├────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┼────────────────┼────────────┤    
  │ B3. Multi-Query Parallel   │ LLM 同時生成 3 個不同角度 query，並行      │ +1 call + 3x retrieval    │ +500ms（平行） │ 中         │    
  │                            │ retrieval 後 merge                         │                           │                │            │    
  ├────────────────────────────┼────────────────────────────────────────────┼───────────────────────────┼────────────────┼────────────┤    
  │ B4. Dedicated Memory Query │ 把 retrieval 做成 sub-agent（與 Phase 46   │ +1 sub-agent cycle        │ +1-2s          │ 高         │    
  │  Agent                     │ Expert Registry 對齊）                     │                           │                │            │    
  └────────────────────────────┴────────────────────────────────────────────┴───────────────────────────┴────────────────┴────────────┘    

  推薦分階段：
  - Phase A（1 Sprint）：B1 Inline topic gen — 最小改動，快速驗證效果
  - Phase B（2 Sprints）：B3 Multi-query parallel — 若 A 效果好，擴展
  - Phase C（長期）：B4 Memory Query Agent — 與 Expert Registry 整合

  B.4 Tenant-Aware Active Retrieval（A ⊗ B 交集）

  這是關鍵整合點：

  # pseudocode
  async def step1_memory_read(ctx):
      # B: Active Retrieval
      topic = await llm.generate_topic(ctx.user_query, ctx.recent_dialog)

      # A: Tenant scoping (強制)
      scope = {
          "org_id": ctx.user.org_id,          # 必填
          "workspace_id": ctx.user.workspace_id,
          "user_id": ctx.user.user_id,
          "agent_id": ctx.agent.agent_id,
      }

      # Retrieval with scope filter
      candidates = await unified_memory.search(
          query=topic,              # ← topic，不是原 query
          scope=scope,              # ← 強制 filter
          memory_types=[...],       # optional
          top_k=20,
      )

      # Rerank + budget
      reranked = await reranker.rerank(ctx.user_query, candidates, top_n=5)
      ctx.memory_text = context_budget.apply(reranked)

  安全設計要點：
  1. scope 由 middleware 從 JWT 注入，絕不從 request body 接受（防偽造）
  2. scope.org_id 強制非空，Qdrant 查詢層面 enforce
  3. Audit log 記錄每次 retrieval 的 (scope, topic, hit_count)

  B.5 Fallback 設計（當 topic gen 失敗）

  LLM topic gen fail / timeout
    ↓
  Fallback to raw user_query embedding
    ↓
  Warn log + metric alert（topic_gen_failure_rate）

  ---
  C — 推薦的 MVP Slice（4 個 Sprint）

  ┌────────┬─────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────┐   
  │ Sprint │                                      內容                                       │                 可驗收                  │   
  ├────────┼─────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤   
  │ S1     │ Tenant scope infra（metadata schema + JWT middleware + Qdrant filter）+         │ 所有新寫入帶 scope；查詢強制 filter     │   
  │        │ 非破壞性 rollout（舊 memory 預設 org_id="default"）                             │                                         │   
  ├────────┼─────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤   
  │ S2     │ B1 Inline Topic Gen + LLM prompt 調優 + benchmark（LongMemEval subset）         │ Topic gen success rate > 90%；retrieval │   
  │        │                                                                                 │  accuracy 提升可量測                    │   
  ├────────┼─────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤   
  │ S3     │ Cohere Rerank 3 整合（Doc 08 quick win）                                        │ Precision@5 提升 ≥ 15%                  │   
  ├────────┼─────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤   
  │ S4     │ Promotion path API（user → workspace）+ HITL approval flow + 最小 UI            │ 可人工將個人 best practice              │   
  │        │                                                                                 │ 升級為團隊共享                          │   
  └────────┴─────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────┘   

  不在 MVP scope：
  - 6-component schema（延後到 Phase 2）
  - Graphiti 整合（延後）
  - InMemory P0 遷移（應另起獨立 sprint，不應 block 此設計）

  ---
  D — 討論時要 align 的決策點

  請您 review 以下決策點，我們逐條討論：

  1. Tenant 粒度：4 層（org/workspace/user/agent）合不合 RAPO / IPA 實際場景？會不會過度複雜？
  2. 儲存方案：A4 hybrid（L3 collection-per-org）對預計租戶數（10? 100? 1000?）是否合適？
  3. Active Retrieval 成本：每 query 多一次 LLM call（即便是 gpt-5-nano），在預計 QPS 下成本接受嗎？
  4. Promotion path：是否真的需要（還是個人 memory 保持個人就好）？
  5. 與 Expert Registry（Phase 46）的關係：agent-level memory 是否應綁 expert definition？

  哪一點想先深入？
==================================================================

==================================================================
❯ 我想知道現在本項目的memory 功能流程是如何運作的, 是屬於哪一種類型的memory 架構設計 (是以CC的設計為基礎?) 現在的預期運行效果又是如何的?                                              我需要先了解清楚本項目已經開發了的功能內容, 才更能有概念有什麼是需要改善和優化的                
                                                                                                                                           
● 好問題。我需要深入現有代碼去看實際行為，而不是只看文件描述。讓我系統地探索。                                                             

  Searched for 3 patterns, read 1 file (ctrl+o to expand)                                                                                  

● 讓我派一個 Explore agent 深入分析這些檔案，這樣能保持上下文窗口精簡並產出結構化報告。                                                    
                                                                                                                                           
● Explore(Analyze current memory system implementation)                                                                                    
  ⎿  Done (10 tool uses · 68.0k tokens · 49s)                                                                                              
  (ctrl+o to expand)                                                                                                                       
                                                                                                                                           
● IPA 記憶系統現狀報告                                                                                                                                                                                                                                                                
  一、架構源流：Claude Code 骨架 + Mem0 引擎的自創混合                                                                                                                                                                                                                                
  代碼裡明確標示 "CC Equivalent"（多處註解直接寫出）：                                                                                                                                                                                                                                
  ┌──────────────┬────────────────────────────┬──────────────────────────────────────┐                                                       │     面向     │          CC 對應           │               IPA 實作               │                                                       ├──────────────┼────────────────────────────┼──────────────────────────────────────┤                                                       │ 系統提示組裝 │ buildEffectiveSystemPrompt │ context_budget.py:4-8 直言對應       │                                                     
  ├──────────────┼────────────────────────────┼──────────────────────────────────────┤
  │ 背景整理     │ autoDream 4-phase          │ consolidation.py:4-18 擴展為 5-phase │
  ├──────────────┼────────────────────────────┼──────────────────────────────────────┤
  │ 抽取類型     │ STABLE / TRANSIENT         │ extraction.py:31-62 同款區分         │
  ├──────────────┼────────────────────────────┼──────────────────────────────────────┤
  │ 記憶層       │ CLAUDE.md + 搜尋索引       │ 擴展成 4 層（見下）                  │
  └──────────────┴────────────────────────────┴──────────────────────────────────────┘

  不是純 CC，也不是純 Mem0：用 CC 的組裝策略 + Mem0/Qdrant 的向量引擎，自創 4 層結構。

  二、實際層級（V9 文件寫 3 層，但代碼有 4 層）

  PINNED_KNOWLEDGE    ← 永不過期（相當於 CLAUDE.md）
  WORKING (Redis)     ← 30 分 TTL（session 內近期事件）
  SESSION (Redis*)    ← 7 天 TTL（*設計是 PostgreSQL，實際只有 Redis）
  LONG_TERM (mem0)    ← 永久（向量搜尋）

  三、End-to-End 運作流程

  Step 1 Memory Read（pipeline 進入）:
  context.task (原始 user query)
    ↓ (沒做任何 transformation)
  ContextBudgetManager.assemble_context()
    ├─ PINNED → 30% token budget（始終注入）
    ├─ WORKING → 25%（Redis 近期）
    ├─ RELEVANT → 30%（mem0 語義搜尋）
    └─ HISTORY → 15%（時序）
    ↓
  memory_text → 注入下游 LLM prompt

  Step 8 PostProcess（pipeline 完成後）:
  Fire-and-forget 異步觸發：
    ├─ ExtractionService: LLM 抽取 FACTS/PREFERENCES/DECISIONS/PATTERNS
    │                     自動寫 LONG_TERM
    └─ ConsolidationService: 每 20 次 pipeline 觸發一次
       ├─ Phase 1: 去重       ✅ 實作
       ├─ Phase 2: 衰減       ❌ 只 log 不寫入
       ├─ Phase 3: 晉升       ❌ 邏輯在，但依賴 access_count（從不更新）
       ├─ Phase 4: 剪枝       ✅ 實作
       └─ Phase 5: 摘要       ❌ 無實現

  四、預期運行效果（基於代碼判斷）

  ┌─────────────────────┬─────────┬──────────────────────────────────────────────────┐
  │        能力         │  狀態   │                       說明                       │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ 多輪對話記憶        │ ✅ 可用 │ WORKING + PINNED 注入每個 prompt                 │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ 跨 session 用戶偏好 │ ✅ 可用 │ 自動抽取 EXTRACTED_PREFERENCE 到 LONG_TERM       │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ 自動整理            │ ⚠️ 半殘 │ 5 階段中只有 2 個真運作                          │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ 重要記憶升級        │ ❌ 壞掉 │ access_count 從不更新 → Phase 3 Promote 永不觸發 │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ Tenant 隔離         │ ⚠️ 弱   │ 只靠 user_id，無 org/workspace 分層              │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ Active Retrieval    │ ❌ 沒有 │ Step 1 直接用原始 query 搜尋，無 topic 生成      │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ Bitemporal          │ ❌ 沒有 │ 只有 created_at/accessed_at，無 event time       │
  ├─────────────────────┼─────────┼──────────────────────────────────────────────────┤
  │ Procedural memory   │ ❌ 沒有 │ types.py 無 SKILL 類型                           │
  └─────────────────────┴─────────┴──────────────────────────────────────────────────┘

  五、三個關鍵「寫了但沒接好」的問題

  1. access_count 從未更新 — types.py:96-97 定義了欄位，但 unified_memory.py search 路徑從不 increment → 整個 Phase 3 Promote 邏輯成死碼   
  2. Session L2 不是設計的 PostgreSQL — unified_memory.py:287 註解承認「In production, this would use PostgreSQL」
  3. Mem0 同步呼叫卡 asyncio — mem0_client.py:238, 283 同步 call 在 async 方法內，未 asyncio.to_thread 包裝

  六、整體判斷

  設計成熟度：B（CC 骨架完整、token 預算精細）
  實作完成度：C+（5-phase consolidation 只跑 2 個、access tracking 斷鏈）
  企業就緒度：C（無 multi-tenant、無 bitemporal、無 audit scope）

  ---
  關鍵啟示給優化方向:
  - 先修「寫了但沒接好」的東西（access_count、Session 層）比加新能力更高 ROI
  - CC 骨架已經建好，企業化等於補 tenant scope + bitemporal + active retrieval 三件
  - 不用另起爐灶，沿著 CC 路線擴展即可

  現在您對現狀有完整概念了，想從哪個方向開始討論優化？
==================================================================

==================================================================

❯ 1. 先解決 :  先修「寫了但沒接好」的東西（access_count、Session 層）比加新能力更高 ROI , 2. 之後再處理 : CC 骨架已經建好，企業化等於補       tenant scope + bitemporal + active retrieval 三件                                                                                         
                                                                                                                                            
● 記憶系統改善 Roadmap（分兩階段）                                                                                                          

  Phase 1 — 修復「寫了但沒接好」（3 Sprints，高 ROI）                                                                                                                                                                                                                                   
  Sprint 1.1 — Access Tracking 斷鏈修復                                                                                                                                                                                                                                                 
  目標：讓 Phase 3 Promote 真正工作
                                                                                                                                              ┌──────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────┬──────┐               │                                     工作項目                                     │              檔案               │ 難度 │             
  ├──────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────┼──────┤
  │ UnifiedMemoryManager.search() 每次命中 increment access_count + 更新 accessed_at │ unified_memory.py               │ 低   │
  ├──────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────┼──────┤
  │ mem0 層級寫回 access metadata（mem0 本身支援 metadata update）                   │ mem0_client.py                  │ 中   │
  ├──────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────┼──────┤
  │ 加 unit test：search → 驗證 access_count 遞增 → 5 次後 promote 觸發              │ tests/unit/integrations/memory/ │ 低   │
  └──────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────┴──────┘

  驗收：連續 search 同一 memory 5 次後，Phase 3 Promote 實際將其升級為 LONG_TERM（可查 Qdrant 確認）

  Sprint 1.2 — Consolidation 半殘補完

  目標：5-phase 全部真正運作

  ┌───────────────────┬───────────────┬───────────────────────────────────────────────────────────┐
  │       Phase       │     現狀      │                           修復                            │
  ├───────────────────┼───────────────┼───────────────────────────────────────────────────────────┤
  │ Phase 2 Decay     │ 只 log 不寫入 │ 實作 importance 按時間衰減，寫回 mem0 metadata            │
  ├───────────────────┼───────────────┼───────────────────────────────────────────────────────────┤
  │ Phase 5 Summarize │ 無實現        │ 用 LLM 對 low-importance cluster 做摘要，原記憶移至冷儲存 │
  └───────────────────┴───────────────┴───────────────────────────────────────────────────────────┘

  驗收：觸發 consolidation 後，Qdrant 可觀察到 importance 下降、summary 記憶新增

  Sprint 1.3 — Session L2 + Mem0 Async

  目標：補完架構設計與消除 async 阻塞

  ┌────────────────────────────┬────────────────────────────────────────────────────┐
  │            工作            │                        說明                        │
  ├────────────────────────────┼────────────────────────────────────────────────────┤
  │ Session L2 落地 PostgreSQL │ 新增 session_memory 表 + ORM + 從 Redis 遷移邏輯   │
  ├────────────────────────────┼────────────────────────────────────────────────────┤
  │ Mem0 async 包裝            │ mem0_client.py 所有同步 call → asyncio.to_thread() │
  ├────────────────────────────┼────────────────────────────────────────────────────┤
  │ 效能 benchmark             │ 驗證 pipeline P95 latency 沒退化                   │
  └────────────────────────────┴────────────────────────────────────────────────────┘

  驗收：Session 記憶進程重啟後仍在；asyncio event loop 無阻塞警告

  ---
  Phase 2 — 企業化三件（5 Sprints，核心能力）

  Sprint 2.1 — Tenant Scope 基建（1 Sprint）

  MemoryEntry 加欄位：org_id / workspace_id / user_id / agent_id
  JWT middleware 注入 scope（不接受 body 傳入）
  Qdrant collection 命名規則：ipa_memory_{org_id}
  UnifiedMemoryManager.search() 強制帶 scope filter
  驗收：不同 org 的 memory 完全不可見；audit log 記錄每次 retrieval 的 scope

  Sprint 2.2 — Bitemporal 支援（1 Sprint）

  MemoryEntry 新增：event_time (真實發生) + ingestion_time (系統記錄)
  Search API 支援 as_of_time 參數（時光機查詢）
  Audit 不可變性 enforce（不允許 UPDATE，只能 supersede）
  驗收：能查「我 2026-04-01 知道的 policy」vs「今天的 policy」

  Sprint 2.3 — Active Retrieval（2 Sprints）

  S2.3.1: Topic Generation Step
    新增 Step1.5：用 gpt-5-nano 從 query + dialog 生成 topic
    Topic → embedding search（取代原始 query）
    Fallback：LLM fail 時降回原始 query

  S2.3.2: Multi-Strategy Retrieval
    並行執行：topic embedding / keyword BM25 / importance filter
    Cohere Rerank 3 整合
    LongMemEval subset benchmark 驗證
  驗收：Retrieval precision@5 ≥ 15% 提升；「save 過但 recall 不到」case 明顯減少

  Sprint 2.4 — 整合驗證（1 Sprint）

  Tenant + Bitemporal + Active Retrieval 三者整合 E2E 測試
  企業場景 use case 演練（multi-tenant HITL approval + audit trail）
  文件 + Developer UI 更新

  ---
  總覽

  ┌─────────┬───────────┬────────────────────────────────────────┬───────────────────────────────────┐
  │  階段   │  Sprints  │                  重點                  │               風險                │
  ├─────────┼───────────┼────────────────────────────────────────┼───────────────────────────────────┤
  │ Phase 1 │ 3         │ 修復既有 bug、補完 consolidation       │ 低（既有骨架已在）                │
  ├─────────┼───────────┼────────────────────────────────────────┼───────────────────────────────────┤
  │ Phase 2 │ 5         │ Tenant + Bitemporal + Active Retrieval │ 中（Active Retrieval 成本需驗證） │
  ├─────────┼───────────┼────────────────────────────────────────┼───────────────────────────────────┤
  │ 合計    │ 8 Sprints │ 約 2-2.5 月（若專注）                  │ —                                 │
  └─────────┴───────────┴────────────────────────────────────────┴───────────────────────────────────┘

  建議的後續步驟

  1. 先建立 plan + checklist 文件（按 feedback_sprint_planning_workflow.md 的規矩）
  2. 決定是否先跑 PoC 驗證 Active Retrieval 的成本/效果
  3. 檢查 memory worktree branch 是否需要 rebase

  請問：
  - 您同意這個 8-Sprint 切分嗎？
  - 要不要先為 Sprint 1.1 起草正式 plan + checklist？
  - 還是想先就某個細節深入討論（例如 Phase 2 Decay 的衰減公式、Session L2 的 PostgreSQL schema）？
==================================================================

==================================================================
● Sprint 171 push 成功。e77240f → 196ad29（2 新 commits）到 origin。                                                                                    
                                                                                                                                                        
● Sprint 171 執行完成總結  
                                                                                                                                                          ┌──────────────────────────────────────────────────────┬────────┬────────────────────────────────────────────────┐
  │                         Task                         │ Status │                      產出                      │                                      ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤                                    
  │ S171-T1~T2 — Config + metadata 欄位                  │ ✅     │ types.py 加 5 config + superseded/summarized   │                                    
  ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤
  │ S171-T3 — update_importance() dispatcher             │ ✅     │ unified_memory.py + mem0_client.py             │                                      ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤
  │ S171-T4 — Phase 2 Decay 實作                         │ ✅     │ exp(-λ*days) + writeback fire-and-forget       │                                    
  ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤                                    
  │ S171-T5 — Phase 5 Summarize（含 v2 CRITICAL 防注入） │ ✅     │ 3 層防護：system prompt + sanitise + validator │                                      ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤
  │ S171-T6 — Phase 4 Prune counter cleanup              │ ✅     │ cleanup-before-delete 次序                     │                                      ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤                                    
  │ S171-T7 — Observability                              │ ✅     │ 結構化 log（metrics 留 deferred）              │                                    
  ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤
  │ S171-T8~T11 — 4 測試檔                               │ ✅     │ 38/38 PASS in 1.10s                            │
  ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤
  │ S171-T12 — quality checks                            │ ✅     │ black/isort/flake8 clean                       │
  ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤
  │ S171-T13 — checklist + progress                      │ ✅     │ 32/43 checked                                  │
  ├──────────────────────────────────────────────────────┼────────┼────────────────────────────────────────────────┤
  │ S171-T14 — commit + push                             │ ✅     │ 196ad29 at origin                              │
  └──────────────────────────────────────────────────────┴────────┴────────────────────────────────────────────────┘

  Branch research/memory-system-enterprise 進度：main + 8 commits（Phase 48 規劃 4 + Sprint 170 實作 2 + Sprint 171 實作 2）。

  AC 得分：8 PASS + 2 deferred（prometheus metrics + integration E2E 需 infra）。零 RED。

  Bug fix 副作用：_prune_stale 時區不一致（pre-existing bug）順手修復。

  下一步選項：
  1. Sprint 172（Session L2 PostgreSQL + mem0 async 完整包裝）— 已解鎖
  2. 等 ADR-048 review 回饋
  3. 安排 staging 跑 integration test（S170 + S171 一併驗）

==================================================================

==================================================================
● Sprint 172 push 成功。196ad29 → 01fb573（3 新 commits）到 origin。

● Sprint 172 執行完成總結               

  ┌──────────────────────────────────────────┬────────┬──────────────────────────────────────────────────┐
  │                   Task                   │ Status │                       產出                       │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T1 — 探索 base pattern              │ ✅     │ SQLAlchemy 2.0 + BaseRepository                  │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T2 — SessionMemory ORM              │ ✅     │ 新 model + 註冊 init                             │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T3 — SessionMemoryRepository        │ ✅     │ CRUD + upsert + delete_expired                   │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T4 — Alembic migration 009          │ ✅     │ up/down + 3 indexes                              │                                                ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T5 — Settings (L2 + mem0)           │ ✅     │ 3 新 config fields                               │                                                ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤                                              
  │ S172-T6 — mem0 full async (8 call sites) │ ✅     │ _run_read / _run_mutate + Mem0LockTimeout        │                                              
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤                                              
  │ S172-T7 — Dual-write + PG-first read     │ ✅     │ PG-first authoritative + Redis cache best-effort │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤                                              
  │ S172-T8 — Backfill script                │ ✅     │ idempotent + least-privilege doc                 │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T9 — mem0 async benchmark           │ ✅     │ heartbeat probe + P95 gate 10ms                  │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T10~T12 — 3 test files (21 tests)   │ ✅     │ 59/59 PASS in 2.05s                              │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T13 — integration test              │ ✅     │ testcontainers PG+Redis (auto-skip)              │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T14 — quality checks                │ ✅     │ 3 bugs fixed (F401/F841 + ORM metadata clash)    │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T15 — checklist + progress          │ ✅     │ 38/50 checked                                    │
  ├──────────────────────────────────────────┼────────┼──────────────────────────────────────────────────┤
  │ S172-T16 — 3 commits + push              │ ✅     │ 01fb573 at origin                                │
  └──────────────────────────────────────────┴────────┴──────────────────────────────────────────────────┘

  Branch 進度：main + 11 commits（Phase 48 規劃 4 + S170 實作 2 + S171 實作 2 + S172 實作 3）。

  AC 得分：7 PASS + 1 partial + 2 deferred-for-infra。零 RED。

  關鍵 bug fix：ORM metadata 保留名衝突 → column 改名 extra_metadata（model + migration + repo 一致）。

  下一步選項：
  1. Sprint 173（Tenant Scope Foundation）— 要等 ADR-048 sign-off
  2. 等 ADR-048 review 回饋（backend + sec + SRE leads）
  3. 安排 staging 跑 alembic upgrade + 3 套 integration tests + 2 套 benchmarks

✻ Worked for 15m 59s     

※ recap: Phase 48 記憶系統改善：Sprint 170-172 已完成並 push 到 `research/memory-system-enterprise`（59/59 tests PASS）。下一步等你決定是推進 Sprint 
  173（需 ADR-048 sign-off）還是安排 staging 跑 integration + benchmark 驗 deferred AC。
  
  49 tasks (48 done, 1 open)
  ◻ [條件] 處理 ADR-048 review 回饋    
  ✔ 建立 ADR-048 review 請求文件
  ✔ 捕捉 pre-change benchmark baseline (AC-6)               
  ✔ 修改 types.py — access_count 預設值
  ✔ 建立 background_tasks.py — 安全 fire-and-forget 工具
  ✔ 修改 mem0_client.py — thread-safe metadata update
  ✔ 修改 unified_memory.py — counter key + tracking hooks
  ✔ 修改 consolidation.py — PINNED guard + force_run + counter cleanup                                                                                    ✔ 撰寫 test_background_tasks.py（4 項測試）
  ✔ 撰寫 test_access_tracking.py（4 tier 測試）                                                                                                            … +39 completed                                                           
==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

==================================================================

