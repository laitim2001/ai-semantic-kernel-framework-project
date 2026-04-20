# 06 - Ontology 專題：Build vs Buy + Graphiti-First 路線

**範圍**：Ontology 自建可行性、4 條路線對比、Graphiti 深入、Microsoft Fabric IQ 對比

---

## 一、Microsoft Fabric IQ Ontology 係咩

**核心定位**：Microsoft 2025-11 Ignite 推出嘅 **Fabric IQ workload** 嘅核心 component，目前係 **public preview**

**佢做咩**：
- 將 OneLake 入面嘅 raw table（SAP vendor table、invoice table）binding 成 business entity（Vendor、Invoice、Contract）
- 定義 properties + relationships + rules
- AI agent / Power BI / Fabric Maps 全部 share 同一個 semantic layer

**核心特色**：
- **No-code 介面** — business analyst 可以建 ontology
- **可由 Power BI semantic model 自動生成**
- **Bound to live data** — query ontology 等於 query underlying data，唔係 separate copy
- **將會通過 MCP endpoint 暴露俾 external agent**（roadmap）
- **Rules + Actions via Fabric Activator** — entity 上可掛 condition-action rule

**重要限制**：
- Public preview，**唔係 production-ready**
- 只支援 DirectLake mode（Import / DirectQuery 唔支援）
- 數據**必須喺 OneLake** — SAP data 要 mirror / shortcut 過去
- 手動 ontology building，冇 auto-discovery
- Decimal type 有 bug

**對 IPA Platform 嘅意義**：如果已 commit Microsoft stack（Azure SSO + Entra OBO），Fabric IQ 係最低阻力 path 去 build L3。但要等 GA（預計 2026 中後段）。

**對比 Palantir Foundry Ontology**：Palantir 14 年領先，功能更深更成熟，但極貴 + lock-in；Microsoft 後發，ecosystem 更開放（MCP）。

---

## 二、自建 Ontology 嘅 4 條路線

### 路線 1：Ontology-Lite（Pydantic + PostgreSQL/Neo4j）⭐

**核心思路**：
- Pydantic 定義 entity types、properties、relationships
- Schema validation 喺 boundary 強制執行
- 唔做 inference，直接 query
- Closed World Assumption（符合 application logic）

**Pydantic 示例**：
```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class Vendor(BaseModel):
    vendor_id: str = Field(..., pattern=r"V\d{4}")
    legal_names: list[str]
    domain: str | None
    owner_dept: Literal["Procurement", "Finance", "Operations"]
    contracts: list[str] = []
    valid_from: datetime
    valid_to: datetime | None = None

class Invoice(BaseModel):
    invoice_id: str
    vendor_id: str
    invoice_type: Literal["FREIGHT", "SERVICE", "GOODS"]
    amount_usd: float = Field(..., gt=0)
    issue_date: datetime
    line_items: list["InvoiceLineItem"]
```

**Storage 選擇**：
- Phase 1：PostgreSQL + JSONB（最簡單，已有 infra）
- Phase 2：Neo4j（需 multi-hop traversal 時）

**Optional libraries**：
- **Neontology** — Pydantic-to-Neo4j OGM
- **SQLModel** — Pydantic + SQLAlchemy 統一

**Effort estimate**：
- Schema design + storage + CRUD：3-4 週
- Entity resolution（RapidFuzz + LLM judge）：2-3 週
- Query API（function tools）：1-2 週
- **Total Phase 1：6-9 週**

**優劣**：
- ✅ 完全控制、無 vendor lock-in、無 preview 限制
- ❌ 冇 visual editor、冇 auto-binding、冇 inference engine

---

### 路線 2：Graphiti-First（Ontology + Memory + KG 三合一）⭐⭐ 強烈推薦

**為咩 game-changer**：一個 framework **同時搞掂 L3 Ontology + L4-Q3 Agentic Memory + L6 Bitemporal Audit 三層**

**Graphiti 內建 features**：
- **Prescribed Ontology**：用 Pydantic 定義 entity / edge types
- **Learned Ontology**：俾 LLM 由 raw data 學 schema
- **Bitemporal**：每個 fact 有 event_time + ingestion_time
- **Hybrid retrieval**：semantic + BM25 + graph traversal
- **Multiple backend**：Neo4j / FalkorDB / Kuzu / Neptune
- **MCP server included**
- **Apache 2.0**

**Code 示例**：
```python
from graphiti_core import Graphiti
from pydantic import BaseModel

class Vendor(BaseModel):
    legal_names: list[str]
    owner_dept: str

class Contract(BaseModel):
    vendor_id: str
    valid_from: str
    valid_to: str

class HasContract(BaseModel):
    relationship: str = "vendor_has_contract"

graphiti = Graphiti(
    "neo4j://localhost:7687",
    "neo4j", "password",
    entity_types={"Vendor": Vendor, "Contract": Contract},
    edge_types={"HAS_CONTRACT": HasContract}
)

# Ingest raw data，Graphiti 自動 extract entities
await graphiti.add_episode(
    name="invoice_2026_03_15",
    episode_body="RICOH HK 提交 freight invoice INV-2026-0312...",
    reference_time=datetime(2026, 3, 15)
)

# Query (bitemporal-aware)
results = await graphiti.search(
    "RICOH HK contracts valid in March 2026",
    center_node_uuid=ricoh_vendor_uuid
)
```

**Effort estimate**：
- Setup Graphiti + Neo4j + schema：1-2 週
- 5-10 entity prescribed ontology：2-3 週
- Integration with IPA（MAF tools）：2 週
- Production hardening：2-3 週
- **Total Phase 1：7-10 週**，但同時 deliver 三層

**優劣**：
- ✅ 三層一次過、production-grade、bitemporal built-in、MCP server included
- ⚠️ Learning curve 1-2 週、Neo4j ops、無 enterprise SLA（除非用 Zep Cloud）

---

### 路線 3：重型 OWL/RDF（Stardog / Apache Jena）

**唔建議**。原因：
1. Open World Assumption vs application Closed World Assumption mismatch
2. OWL reasoner 性能 overhead
3. Tooling 學習曲線陡峭（Protégé、SPARQL、RDF triplestore）
4. Enterprise license 貴
5. 2026 industry consensus：OWL/RDF 為重 reasoning 場景（pharma、regulatory），唔係一般 enterprise

**何時考慮**：RAPO 不屬於呢類，Skip

---

### 路線 4：LLM-Assisted Ontology Generation

**新興路線**（2025-2026 學術活躍方向）：用 LLM 由 unstructured document 自動 extract ontology

**代表**：
- **OntoEKG**（arXiv:2602.01276, 2026/02）：text → Pydantic schema → RDF Turtle
- **deepsense.ai LLM-driven KG construction**

**Pattern**：
```
Unstructured documents
        ↓ Ontology Extraction LLM
        ↓ Pydantic schema validation
        ↓ Hierarchy construction
        ↓ rdflib serialization
RDF/OWL ontology
```

**定位**：**輔助工具而非主路線**。用嚟由 RAPO 50-100 份 representative document propose ontology schema，engineer review + refine，save 50%+ schema design 時間。

---

## 三、推薦路線（針對 IPA Platform）

**最務實 recommendation：路線 2 (Graphiti) + 路線 4 (LLM-assisted) 組合**

```
Week 1-2:   LLM-assisted schema discovery
            └─ 餵 RAPO 50-100 份 document 俾 Claude
            └─ 提取候選 entity types + relationships
            └─ Engineer review，定 5-10 個 V1 entity

Week 3-6:   Graphiti setup + Pydantic schema
            └─ Neo4j deployment
            └─ Entity & edge type definitions
            └─ Initial data ingestion（vendor master, contract list）

Week 7-8:   Integration with IPA Orchestrator
            └─ Wrap as MAF function tools
            └─ Active Retrieval pattern
            └─ Entity resolution helper

Week 9-10:  Production hardening + monitoring
```

**Total：10 週 deliver L3 Ontology + L4-Q3 Agentic Memory + L6 partial Bitemporal**

比等 Fabric IQ GA 仲快，完全 own stack。

---

## 四、Graphiti vs Microsoft Fabric IQ Decision Matrix

| Criteria | Graphiti | Microsoft Fabric IQ |
|----------|----------|---------------------|
| Maturity | Production，enterprise customers | Public preview |
| Bitemporal | ✅ Built-in | ⚠️ Limited |
| Deployment | Self-host (Neo4j) | OneLake dependency |
| Visual Editor | ❌ Pydantic code | ✅ No-code |
| Auto-binding to data | ❌ Manual | ✅ DirectLake auto |
| MCP integration | ✅ Built-in MCP server | 🚧 Planned |
| Agentic memory | ✅ Native | ❌ 要另外 integrate |
| Cost | Apache 2.0 + compute | Fabric capacity cost |
| Lock-in | Low | Medium (Microsoft stack) |
| Ecosystem | Smaller but growing | Large (Microsoft) |
| Best for | Custom enterprise stack | Microsoft-committed orgs |

**對 IPA Platform**：Graphiti 贏，因為:
1. Bitemporal 對 enterprise audit 係剛需
2. 同時 deliver memory + KG + ontology 三層
3. MCP server 天然 fit 你 IPA pattern
4. 唔需要等 preview GA

---

## 五、5-10 個 Entity 入門 Schema（RAPO 建議）

呢個係建議嘅 Phase 1 entity set：

```python
# ─── Core Entities ──────────────────────────────────────────

class Vendor(BaseModel):
    legal_names: list[str]
    vendor_code: str
    domain: str | None
    owner_dept: Literal["Procurement", "Finance", "Operations"]
    country: str | None

class Contract(BaseModel):
    contract_id: str
    contract_type: Literal["MSA", "SOW", "NDA", "Renewal", "Amendment"]
    valid_from: datetime | None
    valid_to: datetime | None
    status: Literal["active", "expired", "terminated", "draft"]

class Invoice(BaseModel):
    invoice_number: str
    invoice_type: Literal["FREIGHT", "SERVICE", "GOODS", "OTHER"]
    amount_usd: float | None
    issue_date: datetime | None
    status: Literal["pending", "approved", "paid", "disputed"]

class Employee(BaseModel):
    employee_id: str
    full_name: str
    department: str | None
    role: str | None
    manager_id: str | None

class IncidentCase(BaseModel):
    case_id: str
    severity: Literal["P1", "P2", "P3", "P4"]
    status: Literal["open", "investigating", "resolved", "closed"]
    root_cause_category: str | None
    resolved_at: datetime | None

class PolicyDocument(BaseModel):
    doc_id: str
    doc_type: Literal["policy", "sop", "runbook", "guideline"]
    effective_from: datetime | None
    owner_dept: str | None
    version: str

# ─── Edge Types ─────────────────────────────────────────────

class HasContract(BaseModel):
    relationship_nature: Literal["primary", "backup", "historical"]

class IssuedBy(BaseModel):
    pass

class ReportsTo(BaseModel):
    since: datetime | None

class InvolvedIn(BaseModel):
    role: Literal["reporter", "affected_party", "resolver", "observer"]

class GovernedBy(BaseModel):
    pass

# ─── Edge Type Map ──────────────────────────────────────────

edge_type_map = {
    ("Vendor", "Contract"): ["HasContract"],
    ("Invoice", "Vendor"): ["IssuedBy"],
    ("Employee", "Employee"): ["ReportsTo"],
    ("Vendor", "IncidentCase"): ["InvolvedIn"],
    ("Employee", "IncidentCase"): ["InvolvedIn"],
    ("Invoice", "PolicyDocument"): ["GovernedBy"],
    ("Contract", "PolicyDocument"): ["GovernedBy"],
}
```

---

## 六、Ontology Schema Evolution

**原則**：從小做起，逐步擴展

**新 entity type 加入**：
```python
# 情境：明年加 Asset management
class Asset(BaseModel):
    asset_id: str
    asset_type: str
    location: str
    owner: str

entity_types["Asset"] = Asset
edge_type_map[("Employee", "Asset")] = ["Uses"]

# 新 episode 用新 schema；舊 episode 不受影響
```

**Schema versioning 策略**：
- 每個 schema change 有 version tag
- Breaking changes 需 data migration plan
- Additive changes（加新 field、新 entity）可以 live

---

## 七、Entity Resolution 嘅挑戰

**呢個係 production 最大 issue，唔係 technical challenge，係 organizational**

### 典型 ambiguity

- SAP：`"Ricoh Hong Kong Ltd"`
- SharePoint contract：`"RICOH HK"`
- Email：`"ricoh-hk.com"`
- ServiceNow ticket：`"Acme HK Limited"`

### Graphiti 嘅 entity resolution

Graphiti 用 LLM dedup，準確率約 85-90%。**10-15% 需 human review**。

### Review Workflow

```python
async def review_entity_duplicates(graphiti):
    vendors = await graphiti.driver.execute_query(
        "MATCH (n:Vendor) RETURN n"
    )
    
    from rapidfuzz import fuzz
    duplicates = []
    for i, v1 in enumerate(vendors):
        for v2 in vendors[i+1:]:
            similarity = max([
                fuzz.ratio(n1, n2)
                for n1 in v1.legal_names
                for n2 in v2.legal_names
            ])
            if similarity > 85:
                duplicates.append((v1, v2, similarity))
    
    return duplicates

# 俾 data steward review
# Confirmed duplicates 做 merge
```

### Cross-Department Alignment

**呢個先係真正難嘅地方**：

- 「Vendor」喺 Finance 定義：有 PO 關係嘅 legal entity
- 「Vendor」喺 Procurement 定義：approved supplier list 入面嘅 entity
- 「Vendor」喺 Legal 定義：簽過 contract 嘅 legal entity

**三個 definition 唔一樣**，ontology schema 要 reconcile

**解法**：
- 由一個 department 開始（建議 Procurement，因為 scope 最闊）
- 其他 department 嘅 specific attribute 做 extension
- 定期 cross-department review meeting

---

## 八、Bottom Line

**3 個關鍵 takeaway**：

1. **Ontology 完全可以自建**
   - Graphiti + Pydantic + LLM-assisted schema discovery
   - 10 週 deliver Phase 1
   - 比等 Fabric IQ preview GA 更快更穩

2. **Graphiti 一個 framework 同時搞掂三層**
   - L3 Ontology
   - L4-Q3 Agentic Memory
   - L6 partial Bitemporal Audit

3. **真正風險唔係技術，係 organizational alignment**
   - Cross-department entity definition alignment
   - Entity resolution review workflow
   - Ontology governance process

---

## 九、Reference

### Paper
- arXiv:2602.01276 — OntoEKG（LLM-driven ontology construction）
- arXiv:2501.13956 — Zep/Graphiti

### Docs
- Microsoft Fabric IQ Ontology：https://learn.microsoft.com/en-us/fabric/iq/ontology/overview
- Graphiti：https://github.com/getzep/graphiti
- Graphiti docs：https://help.getzep.com/graphiti

### Tools
- Neontology (Pydantic-to-Neo4j)：https://github.com/ontolocy/neontology
- Neosemantics (RDF/OWL in Neo4j)：https://neo4j.com/labs/neosemantics/

---

*整理自 2026-04 系列討論*
