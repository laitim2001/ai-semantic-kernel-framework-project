# V9 Dependency & Coupling Analysis

> **Scope**: Full backend dependency graph across 27 top-level modules, 792 Python files
> **Date**: 2026-03-30
> **Method**: AST-based import extraction (`r5_extract_imports.py`) + source reading verification
> **Data Source**: `r5-imports.json` -- 219 files with internal imports, 121 cross-module edges, 11 circular dependencies

---

## Table of Contents

1. [Module Dependency Matrix](#1-module-dependency-matrix)
2. [Circular Dependencies](#2-circular-dependencies)
3. [Coupling Metrics](#3-coupling-metrics)
4. [Layer Violation Analysis](#4-layer-violation-analysis)
5. [Critical Dependency Paths](#5-critical-dependency-paths)
6. [ASCII Dependency Graph](#6-ascii-dependency-graph)
7. [Recommendations](#7-recommendations)

---

## 1. Module Dependency Matrix

### 1.1 Fan-In / Fan-Out Summary Table

Fan-in = number of files in other modules that import this module (how much others depend on it).
Fan-out = number of import references this module makes to other modules (how much it depends on others).

| # | Module | Fan-In | Fan-Out | Coupling Ratio | Role |
|---|--------|--------|---------|----------------|------|
| 1 | `integrations/hybrid/` | **58** | **56** | 1.04 | **中央集線器 (Central Hub)** -- 最高耦合模組 |
| 2 | `api/v1/` | 0* | **225** | N/A | **消費者 (Consumer)** -- 純匯入端，42 路由模組 |
| 3 | `infrastructure/database/` | **38** | 1 | 38.0 | **基礎服務 (Foundation)** -- 高被依賴，低外部依賴 |
| 4 | `integrations/agent_framework/` | **36** | 19 | 1.89 | **框架核心 (Framework Core)** -- MAF 整合層 |
| 5 | `integrations/orchestration/` | **35** | 5 | 7.0 | **編排引擎 (Orchestration)** -- 高被依賴 |
| 6 | `core/config` | **24** | 0 | Leaf | **配置根 (Config Root)** -- 純葉節點 |
| 7 | `integrations/claude_sdk/` | **24** | 10 | 2.4 | **SDK 橋接 (SDK Bridge)** |
| 8 | `integrations/swarm/` | **21** | 2 | 10.5 | **群集系統 (Swarm)** -- 高被依賴 |
| 9 | `domain/sessions/` | **19** | 3 | 6.3 | **會話管理 (Session Mgmt)** |
| 10 | `infrastructure/storage/` | **14** | 18 | 0.78 | **儲存抽象 (Storage)** -- 高雙向耦合 |
| 11 | `integrations/ag_ui/` | **11** | 18 | 0.61 | **AG-UI 協議 (Protocol)** -- 雙向耦合 |
| 12 | `integrations/llm/` | **12** | 1 | 12.0 | **LLM 抽象 (LLM Abstraction)** -- 穩定服務 |
| 13 | `integrations/memory/` | **9** | 0 | Leaf | **記憶體服務 (Memory)** -- 純被依賴 |
| 14 | `domain/workflows/` | **8** | 9 | 0.89 | **工作流領域 (Workflow Domain)** |
| 15 | `integrations/mcp/` | **7** | 0 | Leaf | **MCP 服務 (MCP)** -- 自包含 |
| 16 | `domain/orchestration/` | **7** | 0 | Leaf | **編排領域 (Orch. Domain)** |
| 17 | `domain/tasks/` | **7** | 0 | Leaf | **任務領域 (Task Domain)** |
| 18 | `domain/checkpoints/` | **6** | 5 | 1.2 | **檢查點 (Checkpoint)** |
| 19 | `integrations/knowledge/` | **6** | 1 | 6.0 | **知識庫 (Knowledge)** |
| 20 | `infrastructure/redis_client` | **6** | 1 | 6.0 | **Redis 用戶端 (Redis)** |

*\* `api/v1/` has fan-in = 0 because it is the top-level entry point; no other module should import from API routes.*

**Exception**: `domain/files` imports from `api/v1` (see Layer Violations below).

### 1.2 Module Dependency Adjacency List

Complete graph extracted from AST analysis (27 nodes, 121 edges):

| Source Module | Imports From (Targets) |
|---------------|----------------------|
| `api/v1` | core/auth, core/config, core/performance, core/sandbox_config, core/security, domain/* (16 modules), infrastructure/cache, infrastructure/database, infrastructure/storage, integrations/* (11 modules), middleware/rate_limit |
| `integrations/hybrid` | core/performance, core/security, domain/tasks, infrastructure/distributed_lock, infrastructure/storage, infrastructure/workers, integrations/agent_framework, integrations/claude_sdk, integrations/correlation, integrations/knowledge, integrations/llm, integrations/mcp, integrations/memory, integrations/orchestration, integrations/patrol, integrations/rootcause, integrations/swarm |
| `integrations/agent_framework` | core/config, domain/executions, domain/orchestration, domain/workflows, integrations/hybrid, integrations/llm |
| `integrations/ag_ui` | domain/files, integrations/hybrid, integrations/orchestration, integrations/swarm |
| `infrastructure/storage` | core/config, domain/orchestration, infrastructure/redis_client, integrations/ag_ui, integrations/agent_framework, integrations/hybrid, integrations/mcp, integrations/orchestration |
| `integrations/claude_sdk` | core/sandbox_config, infrastructure/storage, integrations/orchestration, integrations/swarm |
| `domain/workflows` | domain/agents, domain/checkpoints, domain/executions, infrastructure/database, integrations/agent_framework |
| `integrations/orchestration` | infrastructure/redis_client, infrastructure/storage, integrations/llm |
| `integrations/swarm` | integrations/ag_ui, integrations/hybrid |
| `domain/checkpoints` | infrastructure/database, integrations/agent_framework |
| `infrastructure/checkpoint` | domain/checkpoints, domain/sessions, integrations/agent_framework, integrations/hybrid |
| `domain/sessions` | domain/agents, infrastructure/database, integrations/llm |
| `domain/auth` | core/security, infrastructure/database |
| `infrastructure/workers` | domain/tasks, infrastructure/storage, integrations/agent_framework, integrations/swarm |
| `domain/agents` | core/config, integrations/agent_framework |
| `integrations/learning` | integrations/memory |
| `integrations/knowledge` | integrations/memory |
| `integrations/n8n` | integrations/mcp |
| `domain/files` | api/v1 |
| `integrations/llm` | core/config |
| `infrastructure/database` | core/config |
| `infrastructure/redis_client` | core/config |
| `middleware/rate_limit` | core/config |
| `core/auth` | core/config |
| `core/security` | core/config |
| `core/factories` | integrations/orchestration |

---

## 2. Circular Dependencies

### 2.1 Overview

R5 AST extraction detected **11 circular dependency cycles** across the module graph. These are classified by severity based on the layers involved and architectural risk.

### 2.2 Circular Dependency Registry

| # | Cycle Path | Length | Severity | Impact Description |
|---|-----------|--------|----------|-------------------|
| C1 | `agent_framework` -> `hybrid` -> `agent_framework` | 2 | **CRITICAL** | 核心框架雙向耦合: MAF 的 execution handler 匯入 hybrid, hybrid 的 orchestrator 匯入 MAF builders. 任何一方重構會立即破壞另一方. |
| C2 | `agent_framework` -> `domain/workflows` -> `agent_framework` | 2 | **CRITICAL** | 跨層雙向耦合: agent_framework 匯入 domain/workflows/models, 而 domain/workflows/service 匯入 agent_framework/core/executor. 違反分層架構. |
| C3 | `hybrid` -> `infrastructure/storage` -> `hybrid` | 2 | **HIGH** | 跨層循環: hybrid 使用 storage, 但 storage/storage_factories.py 反向匯入 hybrid 子模組. Infrastructure 不應依賴 integration 層. |
| C4 | `ag_ui` -> `swarm` -> `ag_ui` | 2 | **HIGH** | 協議層循環: ag_ui features 匯入 swarm events, swarm/worker_executor 匯入 ag_ui SSE events. 兩模組需共享事件介面但方向不明確. |
| C5 | `agent_framework` -> `domain/workflows` -> `domain/checkpoints` -> `agent_framework` | 3 | **HIGH** | 三角循環: 經過 domain 層兩個模組再回到 integration 層, 形成複雜依賴鏈. |
| C6 | `domain/agents` -> `agent_framework` -> `domain/workflows` -> `domain/agents` | 3 | **HIGH** | Domain 層內部透過 integration 層形成環路, agents 匯入 MAF, MAF 匯入 workflows, workflows 匯入 agents. |
| C7 | `hybrid` -> `infrastructure/storage` -> `ag_ui` -> `hybrid` | 3 | **MEDIUM** | 三模組環路: 經 storage 間接連接. storage 匯入 ag_ui thread storage. |
| C8 | `infrastructure/storage` -> `ag_ui` -> `orchestration` -> `infrastructure/storage` | 3 | **MEDIUM** | Infrastructure 層被 integration 模組拉入循環. |
| C9 | `hybrid` -> `infrastructure/storage` -> `ag_ui` -> `swarm` -> `hybrid` | 4 | **MEDIUM** | 四模組長環路: hybrid 經由 storage -> ag_ui -> swarm 回到 hybrid. |
| C10 | `agent_framework` -> `hybrid` -> `infrastructure/storage` -> `agent_framework` | 3 | **MEDIUM** | 經 infrastructure 層的三角循環, storage 反向匯入 agent_framework. |
| C11 | `agent_framework` -> `hybrid` -> `infrastructure/workers` -> `agent_framework` | 3 | **MEDIUM** | 經 infrastructure/workers 的三角循環, workers 匯入 agent_framework 和 swarm. |

### 2.3 Cycle Cluster Analysis

11 個循環可歸納為 **3 個主要耦合叢集**:

```
叢集 A: MAF-Hybrid 核心耦合 (涉及 C1, C5, C6, C10, C11)
  agent_framework <====> hybrid <====> infrastructure/*
  涵蓋 5 個循環, 是系統最嚴重的結構性問題.
  根因: hybrid 同時是 MAF 的使用者和被使用者.

叢集 B: AG-UI/Swarm 協議耦合 (涉及 C4, C7, C8, C9)
  ag_ui <====> swarm, ag_ui <====> hybrid (via storage)
  涵蓋 4 個循環.
  根因: 事件類型定義分散在多個模組, 缺乏統一事件介面.

叢集 C: Domain-Integration 跨層耦合 (涉及 C2, C5, C6)
  domain/* <====> integrations/agent_framework
  涵蓋 3 個循環.
  根因: domain 層直接匯入 integration 層的具體實作, 而非透過抽象介面.
```

### 2.4 Severity Distribution

| Severity | Count | Percentage |
|----------|-------|------------|
| CRITICAL | 2 | 18% |
| HIGH | 4 | 36% |
| MEDIUM | 5 | 46% |

---

## 3. Coupling Metrics

### 3.1 High-Coupling Hotspots

Based on fan-in + fan-out combined metrics:

| Rank | Module | Fan-In | Fan-Out | Combined | Assessment |
|------|--------|--------|---------|----------|------------|
| 1 | **`integrations/hybrid/`** | 58 | 56 | **114** | **God Module** -- 17 outbound dependencies, imported by nearly every integration module. Contains orchestrator, checkpoint, context sync, risk assessment, switching, intent analysis. Should be decomposed. |
| 2 | **`api/v1/`** | 0 | 225 | **225** | Expected for API gateway -- 42 route modules importing from all layers. Fan-out is high but structurally correct. |
| 3 | **`integrations/agent_framework/`** | 36 | 19 | **55** | Moderate concern -- bidirectional coupling with hybrid and domain/workflows. |
| 4 | **`infrastructure/storage/`** | 14 | 18 | **32** | **Layer violation hub** -- imports from integrations (ag_ui, hybrid, mcp, orchestration, agent_framework). Infrastructure should not depend upward. |
| 5 | **`integrations/ag_ui/`** | 11 | 18 | **29** | Tightly coupled to hybrid and swarm internals via feature files. |

### 3.2 Instability Index

Instability = Fan-Out / (Fan-In + Fan-Out). Range: 0 (stable) to 1 (unstable).

Stable modules (I < 0.3) should be depended upon; unstable modules (I > 0.7) should depend on others.

| Module | Fan-In | Fan-Out | Instability | Expected | Actual Status |
|--------|--------|---------|-------------|----------|--------------|
| `core/config` | 24 | 0 | **0.00** | Stable | OK -- Pure leaf, correctly stable |
| `integrations/llm/` | 12 | 1 | **0.08** | Stable | OK -- LLM abstraction, correctly stable |
| `integrations/memory/` | 9 | 0 | **0.00** | Stable | OK -- Pure leaf service |
| `integrations/mcp/` | 7 | 0 | **0.00** | Stable | OK -- Self-contained |
| `infrastructure/database/` | 38 | 1 | **0.03** | Stable | OK -- Foundation service |
| `integrations/orchestration/` | 35 | 5 | **0.13** | Stable | OK -- Core orchestration |
| `integrations/hybrid/` | 58 | 56 | **0.49** | Stable | **WARNING** -- Should be stable (high fan-in) but has I=0.49, meaning it is equally dependent on others. This violates the Stable Dependencies Principle. |
| `infrastructure/storage/` | 14 | 18 | **0.56** | Stable | **VIOLATION** -- Infrastructure should be stable but has more outbound than inbound deps. |
| `integrations/ag_ui/` | 11 | 18 | **0.62** | Moderate | **WARNING** -- Borderline unstable, but many modules depend on it. |
| `api/v1/` | 0 | 225 | **1.00** | Unstable | OK -- Top-level consumer, correctly unstable |

### 3.3 Afferent/Efferent Coupling by Layer

| Layer | Modules | Avg Fan-In | Avg Fan-Out | Layer Role |
|-------|---------|-----------|------------|-----------|
| L11: Infrastructure | database, storage, cache, checkpoint, redis, workers | 19.3 | 7.8 | Should be stable (mostly OK except storage) |
| L10: Domain | sessions, workflows, agents, checkpoints, tasks, orchestration | 8.0 | 2.8 | Should be stable (mostly OK except workflow->MAF) |
| L09: Integrations | hybrid, MAF, claude_sdk, orchestration, ag_ui, swarm, llm, memory, mcp, etc. | 21.9 | 15.3 | Mixed -- some stable (llm, memory), some unstable (hybrid) |
| L02: API | v1/ | 0 | 225 | Correctly unstable |
| L11: Core | config, security, auth, performance | 14.5 | 0.5 | Correctly stable |

---

## 4. Layer Violation Analysis

### 4.1 Expected Layer Dependencies (Top-Down)

```
L02: API/v1          --> can import from: Domain, Infrastructure, Integrations, Core
L03-L09: Integrations --> can import from: Domain, Infrastructure, Core
L10: Domain           --> can import from: Infrastructure, Core
L11: Infrastructure   --> can import from: Core ONLY
L11: Core             --> can import from: (nothing -- leaf layer)
```

### 4.2 Detected Violations

| # | Violation Type | Source (Lower Layer) | Target (Higher Layer) | Severity | Files Involved |
|---|---------------|---------------------|----------------------|----------|---------------|
| V1 | **Infrastructure -> Integration** | `infrastructure/storage/` | `integrations/ag_ui` | **CRITICAL** | `storage_factories.py` imports ag_ui thread storage |
| V2 | **Infrastructure -> Integration** | `infrastructure/storage/` | `integrations/hybrid` | **CRITICAL** | Storage imports hybrid submodules |
| V3 | **Infrastructure -> Integration** | `infrastructure/storage/` | `integrations/agent_framework` | **CRITICAL** | Storage imports MAF components |
| V4 | **Infrastructure -> Integration** | `infrastructure/storage/` | `integrations/mcp` | **HIGH** | Storage references MCP modules |
| V5 | **Infrastructure -> Integration** | `infrastructure/storage/` | `integrations/orchestration` | **HIGH** | Storage references orchestration |
| V6 | **Infrastructure -> Integration** | `infrastructure/checkpoint/` | `integrations/hybrid` | **HIGH** | Checkpoint adapter imports hybrid |
| V7 | **Infrastructure -> Integration** | `infrastructure/checkpoint/` | `integrations/agent_framework` | **HIGH** | Checkpoint adapter imports MAF |
| V8 | **Infrastructure -> Integration** | `infrastructure/workers/` | `integrations/agent_framework` | **MEDIUM** | Worker imports MAF |
| V9 | **Infrastructure -> Integration** | `infrastructure/workers/` | `integrations/swarm` | **MEDIUM** | Worker imports swarm |
| V10 | **Infrastructure -> Domain** | `infrastructure/storage/` | `domain/orchestration` | **HIGH** | Storage factory imports domain memory |
| V11 | **Domain -> Integration** | `domain/workflows/` | `integrations/agent_framework` | **HIGH** | Workflow service imports MAF executor |
| V12 | **Domain -> Integration** | `domain/checkpoints/` | `integrations/agent_framework` | **HIGH** | Checkpoint service imports MAF approval |
| V13 | **Domain -> Integration** | `domain/agents/` | `integrations/agent_framework` | **MEDIUM** | Agent service imports MAF |
| V14 | **Domain -> API** | `domain/files/` | `api/v1` | **CRITICAL** | Domain file service imports from API layer -- completely inverted |
| V15 | **Core -> Integration** | `core/factories` | `integrations/orchestration` | **HIGH** | Core factory imports integration module |

### 4.3 Violation Summary

| Violation Direction | Count | Severity Breakdown |
|--------------------|-------|-------------------|
| Infrastructure -> Integration | 9 | 3 CRITICAL, 4 HIGH, 2 MEDIUM |
| Domain -> Integration | 3 | 2 HIGH, 1 MEDIUM |
| Infrastructure -> Domain | 1 | 1 HIGH |
| Domain -> API | 1 | 1 CRITICAL |
| Core -> Integration | 1 | 1 HIGH |
| **Total** | **15** | **4 CRITICAL, 8 HIGH, 3 MEDIUM** |

### 4.4 Root Cause Analysis

**`infrastructure/storage/` is the worst offender** with 6 violations (V1-V5, V10). Root cause: `storage_factories.py` acts as a service locator that knows about all storage backends across all layers. It imports concrete implementations from ag_ui, hybrid, orchestration, agent_framework, and domain -- turning the infrastructure layer into a dependency magnet.

**`domain/files/` -> `api/v1`** is the most severe architectural violation. A domain service importing from the API layer completely inverts the dependency direction.

---

## 5. Critical Dependency Paths

### 5.1 If Module X Goes Down, What Breaks?

Analysis of the transitive dependency graph to identify blast radius for each critical module.

#### Scenario 1: `integrations/hybrid/` Failure

```
integrations/hybrid/ (fan-in: 58)
  |
  +-- DIRECT dependents:
  |     api/v1 (42 route modules use hybrid)
  |     infrastructure/storage (storage_factories)
  |     infrastructure/checkpoint (checkpoint adapter)
  |     infrastructure/workers (worker executor)
  |     integrations/agent_framework (builders, execution)
  |     integrations/ag_ui (4 feature files)
  |     integrations/swarm (swarm integration bridge)
  |
  +-- TRANSITIVE dependents (via agent_framework):
  |     domain/workflows (executor)
  |     domain/checkpoints (approval)
  |     domain/agents (agent service)
  |
  Blast Radius: ~70% of backend modules
  Assessment: CATASTROPHIC -- hybrid is the single point of failure
```

#### Scenario 2: `infrastructure/database/` Failure

```
infrastructure/database/ (fan-in: 38)
  |
  +-- DIRECT dependents:
  |     domain/auth, domain/sessions, domain/workflows
  |     domain/checkpoints, domain/executions
  |
  +-- TRANSITIVE dependents (via domain services):
  |     api/v1 (all routes needing DB)
  |     integrations/* (via domain layer)
  |
  Blast Radius: ~50% of backend modules
  Assessment: HIGH -- expected for database, mitigated by connection pooling
```

#### Scenario 3: `integrations/agent_framework/` Failure

```
integrations/agent_framework/ (fan-in: 36)
  |
  +-- DIRECT dependents:
  |     api/v1 (workflow, checkpoint, agent routes)
  |     domain/workflows, domain/checkpoints, domain/agents
  |     infrastructure/storage, infrastructure/checkpoint, infrastructure/workers
  |     integrations/hybrid (execution handler)
  |
  +-- TRANSITIVE dependents (via hybrid):
  |     integrations/ag_ui, integrations/swarm
  |     integrations/claude_sdk
  |
  Blast Radius: ~55% of backend modules
  Assessment: CRITICAL -- MAF is second most impactful failure point
```

#### Scenario 4: `core/config` Failure

```
core/config (fan-in: 24)
  |
  +-- DIRECT dependents:
  |     core/auth, core/security
  |     infrastructure/database, infrastructure/redis_client
  |     integrations/llm
  |     integrations/agent_framework
  |     domain/agents
  |     middleware/rate_limit
  |
  +-- TRANSITIVE: Everything (config is the root)
  |
  Blast Radius: 100% of backend
  Assessment: CRITICAL but expected -- config is a leaf dependency
```

### 5.2 Critical Path Summary

| Module | Direct Dependents | Blast Radius | Recovery Complexity |
|--------|------------------|-------------|-------------------|
| `core/config` | 8 | 100% | LOW -- config is static, rarely changes |
| `integrations/hybrid/` | 7 modules (58 files) | ~70% | **VERY HIGH** -- complex module with many internal states |
| `integrations/agent_framework/` | 8 modules (36 files) | ~55% | HIGH -- external SDK dependency |
| `infrastructure/database/` | 5 modules (38 files) | ~50% | MEDIUM -- standard connection recovery |
| `integrations/orchestration/` | 6 modules (35 files) | ~40% | MEDIUM -- routing can degrade gracefully |
| `integrations/llm/` | 4 modules (12 files) | ~30% | LOW -- circuit breaker exists |

---

## 6. ASCII Dependency Graph

### 6.1 Full Module Dependency Map

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                 IPA Platform 模組依賴全景圖                        │
                    │           27 模組, 121 條邊, 11 個循環依賴                        │
                    └─────────────────────────────────────────────────────────────────┘

    [L02: API 層]
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                                                                                 │
    │   api/v1  (fan-out: 225)                                                       │
    │   匯入 42 個子模組 → domain/* (16), integrations/* (11), infra/* (3), core/* (5) │
    │                                                                                 │
    └────┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────────┘
         │          │          │          │          │          │
         ↓          ↓          ↓          ↓          ↓          ↓
    [L10: Domain 層]                          [L09: Integration 層]
    ┌──────────────────────┐                  ┌────────────────────────────────────────┐
    │                      │                  │                                        │
    │  sessions (19 in)    │                  │  ┌──────────────────────────────────┐  │
    │  workflows (8 in) ───┼──────────────────┼─→│  hybrid/ (58 in, 56 out)        │  │
    │  checkpoints (6 in) ─┼──────────────────┼─→│  中央集線器 — 17 個外部依賴       │  │
    │  agents (4 in) ──────┼──────────────────┼─→│  ┌→ agent_framework             │  │
    │  tasks (7 in)        │                  │  │  ├→ claude_sdk                   │  │
    │  orchestration (7 in)│                  │  │  ├→ orchestration                │  │
    │                      │                  │  │  ├→ swarm, ag_ui                 │  │
    │  ⚠ workflows 匯入   │                  │  │  ├→ llm, memory, knowledge       │  │
    │    agent_framework   │                  │  │  ├→ correlation, rootcause       │  │
    │  ⚠ checkpoints 匯入 │                  │  │  ├→ mcp, patrol                  │  │
    │    agent_framework   │                  │  │  └→ infra/storage, infra/workers │  │
    │  ⚠ agents 匯入      │                  │  └──────────────────────────────────┘  │
    │    agent_framework   │                  │         ↑↓ (雙向!)                     │
    │                      │                  │  ┌──────────────────────────────────┐  │
    └──────────────────────┘                  │  │  agent_framework/ (36 in, 19 out)│  │
                                              │  │  MAF 框架整合                     │  │
                                              │  │  → hybrid, llm, domain/*         │  │
                                              │  └──────────────────────────────────┘  │
                                              │                                        │
                                              │  ┌───────────┐  ┌───────────────────┐  │
                                              │  │orchestration│  │  claude_sdk/      │  │
                                              │  │(35 in,5 out)│  │  (24 in, 10 out) │  │
                                              │  └───────────┘  └───────────────────┘  │
                                              │                                        │
                                              │  ┌──────────┐ ┌──────────┐ ┌────────┐ │
                                              │  │ ag_ui/   │↔│ swarm/   │ │  llm/  │ │
                                              │  │(11in,18o)│ │(21in,2o) │ │(12in,1)│ │
                                              │  └──────────┘ └──────────┘ └────────┘ │
                                              │                                        │
                                              │  ┌────────┐┌───────┐┌───────┐┌──────┐ │
                                              │  │memory/ ││knowl. ││patrol/││ mcp/ │ │
                                              │  │(9in,0o)││(6in,1)││(0in,0)││(7,0) │ │
                                              │  └────────┘└───────┘└───────┘└──────┘ │
                                              └────────────────────────────────────────┘
                                                        ↑  (layer violations!)
    [L11: Infrastructure 層]
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                                                                                 │
    │  database/ (38 in, 1 out)     ← 正常: 純粹被依賴                                │
    │  redis_client/ (6 in, 1 out)  ← 正常                                           │
    │  cache/ (被 api 匯入)          ← 正常                                           │
    │                                                                                 │
    │  ⚠ storage/ (14 in, 18 out) → 匯入 ag_ui, hybrid, MAF, mcp, orchestration     │
    │  ⚠ checkpoint/ (0 in, 5 out) → 匯入 hybrid, agent_framework, domain/*          │
    │  ⚠ workers/ (0 in, 4 out)   → 匯入 agent_framework, swarm                     │
    │                                                                                 │
    └─────────────────────────────────────────────────────────────────────────────────┘
                                              ↓
    [L11: Core 層 — 葉節點]
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │  config (24 in, 0 out)  |  security (被依賴)  |  performance (被依賴)           │
    │  ⚠ factories (0 in, 1 out) → 匯入 integrations/orchestration (違規!)           │
    └─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Circular Dependency Visualization

```
    ┌──────────────────────────────────────────────────────────────────────┐
    │                  11 個循環依賴 — 3 個耦合叢集                         │
    └──────────────────────────────────────────────────────────────────────┘

    叢集 A: MAF-Hybrid 核心耦合 (5 cycles, CRITICAL)
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │   agent_framework ←════════════════════→ hybrid             │
    │        │        ↑     (C1: 雙向直接)      │                │
    │        │        │                          │                │
    │        ↓        │                          ↓                │
    │   domain/workflows ←──── C2 ───→ infra/storage             │
    │        │                              │     │              │
    │        ↓                              │     ↓              │
    │   domain/checkpoints                  │ infra/workers      │
    │        │          (C5: 三角)          │  (C11: 三角)       │
    │        └──────────────────────────────┘                    │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘

    叢集 B: AG-UI/Swarm 協議耦合 (4 cycles, HIGH)
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │           ag_ui ←═══════════════→ swarm                    │
    │             │       (C4: 雙向)      │                      │
    │             │                        │                      │
    │             ↓                        ↓                      │
    │       infra/storage ←──── C7,C8,C9 ──→ hybrid              │
    │        (orchestration 也參與 C8)                            │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘

    叢集 C: Domain-Integration 跨層耦合 (3 cycles, HIGH)
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │   domain/agents ──→ agent_framework ──→ domain/workflows   │
    │        ↑               (C6: 三角)           │              │
    │        └────────────────────────────────────┘              │
    │                                                             │
    │   domain/workflows ──→ agent_framework (C2: 雙向)          │
    │   domain/checkpoints ──→ agent_framework (C5: 三角)        │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
```

---

## 7. Recommendations

### 7.1 Priority 1: Decompose `integrations/hybrid/` (CRITICAL)

**Problem**: hybrid/ is a God Module with fan-in=58, fan-out=56, involved in 7 of 11 circular dependencies.

**Solution**:
1. Extract `hybrid/checkpoint/` into `infrastructure/checkpoint/` (it already partially exists there).
2. Extract `hybrid/context/` into a standalone `integrations/context_bridge/` module.
3. Extract `hybrid/risk/` into `integrations/risk_assessment/` module.
4. Keep `hybrid/orchestrator/` as the core, but reduce its imports to only contracts/interfaces.

**Expected impact**: Reduce hybrid fan-out from 56 to ~15, eliminate cycles C1, C3, C7, C9.

### 7.2 Priority 2: Fix Infrastructure Layer Violations (CRITICAL)

**Problem**: `infrastructure/storage/` imports from 5 integration modules, violating layered architecture.

**Solution**:
1. Introduce `infrastructure/storage/contracts.py` defining abstract storage protocols.
2. Move concrete storage factory resolution to `integrations/storage_registry/` or use dependency injection at app startup.
3. Move `infrastructure/checkpoint/adapters/` to `integrations/checkpoint/`.
4. Move `infrastructure/workers/` to `integrations/workers/` (it depends on swarm and MAF).

**Expected impact**: Eliminate violations V1-V10, break cycles C3, C7, C8.

### 7.3 Priority 3: Introduce Domain Interface Layer (HIGH)

**Problem**: 3 domain modules directly import from `integrations/agent_framework`.

**Solution**:
1. Define abstract interfaces in `domain/contracts/`:
   - `WorkflowExecutorProtocol`
   - `ApprovalServiceProtocol`
   - `AgentFrameworkProtocol`
2. Domain modules import only from `domain/contracts/`.
3. `integrations/agent_framework/` implements these protocols.
4. Bind concrete implementations at application startup via dependency injection.

**Expected impact**: Eliminate cycles C2, C5, C6. Fix violations V11-V13.

### 7.4 Priority 4: Unify Event Type System (HIGH)

**Problem**: `ag_ui` and `swarm` have bidirectional imports due to shared event types.

**Solution**:
1. Create `integrations/events/` (or extend `integrations/contracts/`) with all shared event types.
2. Both `ag_ui` and `swarm` import from this shared event package.
3. Remove direct cross-imports between ag_ui and swarm.

**Expected impact**: Eliminate cycle C4, reduce coupling between ag_ui and swarm.

### 7.5 Priority 5: Fix `domain/files` -> `api/v1` Inversion (CRITICAL)

**Problem**: `domain/files/` imports from `api/v1`, completely inverting the architecture.

**Solution**: Move the shared types/utilities that `domain/files` needs from `api/v1` into `domain/` or `core/`. If the import is for route-level constants, extract them to a shared location.

**Expected impact**: Fix violation V14.

### 7.6 Summary Roadmap

| Phase | Action | Cycles Fixed | Violations Fixed | Effort |
|-------|--------|-------------|-----------------|--------|
| Phase A | Fix domain/files -> api/v1 inversion | -- | V14 | 1 sprint |
| Phase B | Introduce domain contracts/interfaces | C2, C5, C6 | V11-V13 | 2 sprints |
| Phase C | Fix infrastructure layer violations | C3, C7, C8, C10 | V1-V10 | 2 sprints |
| Phase D | Decompose hybrid/ module | C1, C9, C11 | -- | 3 sprints |
| Phase E | Unify event type system | C4 | -- | 1 sprint |

**Total estimated effort**: 9 sprints to eliminate all 11 circular dependencies and 15 layer violations.

---

## Appendix A: Data Sources

| Source | Description |
|--------|-------------|
| `scripts/analysis/r5_extract_imports.py` | AST-based import graph extractor |
| `docs/07-analysis/V9/r5-imports.json` | Raw extraction output (219 files, 27 modules, 121 edges, 11 cycles) |
| `docs/07-analysis/V9/06-cross-cutting/cross-cutting-analysis.md` | V9 cross-cutting analysis with security, performance, data flow |
| `docs/07-analysis/V9/01-architecture/layer-09-integrations.md` | Layer 09 integration module analysis |
| `scripts/analysis/r7-codebase-truth.json` | Codebase truth: 1028 files, 327,582 LOC |

---

*Analysis based on AST extraction of 792 backend Python files and source code reading verification of 939+ files across V9 analysis rounds.*
