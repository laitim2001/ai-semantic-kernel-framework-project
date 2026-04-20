# 07 - Ingestion 工程手冊

**範圍**：raw data source → queryable Knowledge Graph 嘅完整 pipeline、多格式 document 處理、持續更新機制

---

## 一、總覽：5-Stage Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 0: SOURCE INVENTORY                                           │
│  盤點所有企業數據 source，分類處理策略                                  │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 1: ONTOLOGY DESIGN                                            │
│  定義 entity types、edge types、prescribed schema                    │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 2: DATA PREPARATION PIPELINE                                  │
│  Structured → JSON episodes                                          │
│  Unstructured → Text chunks with metadata                            │
│  Conversational → Message episodes                                   │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 3: INGESTION EXECUTION                                        │
│  Bulk (historical) + Incremental (real-time)                         │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 4: POST-INGESTION PROCESSING                                  │
│  Entity resolution、community building、index refresh                │
└──────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 5: ONGOING OPERATIONS                                         │
│  Continuous ingestion、monitoring、schema evolution                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 二、Stage 0 - Source Inventory（最多人 skip，最唔應該 skip）

### 4 大 Data Source 類別

| 類別 | Examples | EpisodeType | Strategy |
|------|----------|-------------|----------|
| **A. Structured Master Data** | Vendor master、Employee list、Chart of Accounts | `json` | Bulk one-time + incremental |
| **B. Structured Transactions** | Invoices、POs、expense claims、incidents | `json` | Incremental (event-driven) |
| **C. Unstructured Documents** | Contracts、SOPs、policies、runbooks | `text` | Bulk initial + incremental |
| **D. Conversational** | Support chat logs、email threads、Teams | `message` | Stream-based |

### Deliverable：Source Inventory Spreadsheet

| Source System | Data Type | Category | Volume | Update Freq | Access Method | Owner | Sensitivity |
|--------------|-----------|----------|--------|-------------|---------------|-------|-------------|
| SAP Vendor Master | Vendor records | A | ~5,000 | Daily | BAPI/RFC | Finance | Medium |
| SAP Invoice | Freight invoices | B | ~500/月 | Real-time | IDoc/Webhook | Finance | High |
| SharePoint Contracts | PDF contracts | C | ~2,000 docs | Weekly | MS Graph API | Legal | High |
| ServiceNow Incidents | Tickets + resolution | B | ~1,000/月 | Real-time | SN API | IT Ops | Low |
| Confluence SOPs | Markdown pages | C | ~500 pages | Monthly | Confluence API | All | Low |
| Outlook (Finance) | Email threads | D | ~10k/月 | Real-time | MS Graph | Finance | High |

**呢張表係 ingestion 架構設計嘅 blueprint。冇呢張表直接寫 code，100% scope creep**

---

## 三、Data Source 接入 Pattern

### 4 種接入方式對比

| 方式 | 適用 | 優點 | 缺點 | 建議 |
|------|------|------|------|------|
| **Direct DB** (JDBC/ODBC read) | One-time snapshot | 簡單、快 | 加 source load、冇 event semantics | 只用喺 initial backfill |
| **Event/Webhook** | Real-time transactions | 即時、event semantics、唔加 load | 需要 source 支援 | ✅ **最佳 for transactions** |
| **ETL → DW → Graphiti** | Heavy analytical data | DW 已 cleansed、隔離 production | Stale (T+1)、失去 event timeline | Historical + master data |
| **API (MCP / REST)** | Controlled integration | Standardized、auth enforced | 需要 source 有 API | ✅ **Preferred** |

### 對 IPA Platform 嘅混合 Pattern

```
┌─ Master Data (vendors, employees) ──────────────────────────┐
│  → 每晚 ETL from DW → Graphiti bulk ingest                   │
│  Why: 低頻更新，容忍 T+1                                      │
└──────────────────────────────────────────────────────────────┘

┌─ Transactions (invoices, POs, incidents) ───────────────────┐
│  → SAP/ServiceNow webhook → n8n → Graphiti incremental      │
│  Why: 需要 real-time + precise event_time                    │
└──────────────────────────────────────────────────────────────┘

┌─ Documents (contracts, policies, SOPs) ─────────────────────┐
│  → SharePoint/Confluence API → nightly sync → Graphiti      │
│  Why: 更新中等，需 version tracking                          │
└──────────────────────────────────────────────────────────────┘

┌─ Conversations (emails, Teams, Slack) ──────────────────────┐
│  → MS Graph API/Slack API (streaming) → Graphiti            │
│  Why: High volume，需 scope filtering                        │
└──────────────────────────────────────────────────────────────┘
```

### 為咩唔建議直接駁 source DB

3 個硬性理由：
1. **Source system load** — SAP DBA 會 say no
2. **冇 event semantics** — 只有 snapshot，唔知邊個 event 幾時發生
3. **Schema coupling** — source schema 一變就壞

### Data Warehouse 嘅角色

**DW 係 ingestion 嘅 staging layer，唔係直接 source**

```
SAP → (CDC/ETL) → DW/Lakehouse → Graphiti
                   ↑
         (n8n / Azure Data Factory 已做呢個 layer)
```

IPA Platform 已有 ADF MCP + n8n，即係完美嘅 DW-style intermediate。

---

## 四、Stage 2 - Data Preparation

### 2.1 Category A - Structured Master Data

**Source format**：SAP vendor table

```
VENDOR_CODE | VENDOR_NAME             | COUNTRY | DOMAIN        | DEPT
V0023       | Ricoh Hong Kong Ltd     | HK      | ricoh-hk.com  | Procurement
V0024       | RICOH HK                | HK      | (same)        | (same)  ← alias
```

**Preparation**：

```python
import pandas as pd
import json
from graphiti_core.nodes import EpisodeType, RawEpisode
from datetime import datetime, timezone

async def prepare_vendor_master(csv_path: str) -> list[RawEpisode]:
    df = pd.read_csv(csv_path)
    
    # De-duplicate aliases
    grouped = df.groupby("VENDOR_CODE").agg({
        "VENDOR_NAME": lambda x: list(set(x)),
        "COUNTRY": "first",
        "DOMAIN": "first",
        "DEPT": "first",
    }).reset_index()
    
    episodes = []
    for _, row in grouped.iterrows():
        episode_body = {
            "vendor_code": row["VENDOR_CODE"],
            "legal_names": row["VENDOR_NAME"],
            "country": row["COUNTRY"],
            "domain": row["DOMAIN"],
            "owner_dept": row["DEPT"],
        }
        
        episodes.append(RawEpisode(
            name=f"vendor_master_{row['VENDOR_CODE']}",
            content=json.dumps(episode_body),
            source=EpisodeType.json,
            source_description="SAP vendor master data",
            reference_time=datetime.now(timezone.utc),
        ))
    
    return episodes
```

### 2.2 Category B - Structured Transactions

```python
async def prepare_invoice(invoice_data: dict) -> RawEpisode:
    # 關鍵：用原本 transaction date 做 reference_time
    # 呢個係 bitemporal 嘅核心
    reference_time = datetime.fromisoformat(invoice_data["posting_date"])
    
    episode_body = {
        "invoice_number": invoice_data["doc_num"],
        "vendor_code": invoice_data["vendor_code"],
        "invoice_type": map_invoice_type(invoice_data["doc_type"]),
        "amount_usd": convert_to_usd(
            invoice_data["amount"], 
            invoice_data["currency"]
        ),
        "issue_date": invoice_data["issue_date"],
        "line_items": [
            {
                "description": item["desc"],
                "amount": item["amount"],
                "cost_center": item["cost_center"],
            }
            for item in invoice_data["line_items"]
        ],
    }
    
    return RawEpisode(
        name=f"invoice_{invoice_data['doc_num']}",
        content=json.dumps(episode_body),
        source=EpisodeType.json,
        source_description=f"SAP invoice (source: {invoice_data['source_system']})",
        reference_time=reference_time,
    )
```

### 2.3 Category C - Unstructured Documents（最複雜）

涉及：(1) PDF/Word parsing, (2) Chunking strategy, (3) Metadata preservation

```python
from docling.document_converter import DocumentConverter

async def prepare_contract(contract_pdf_path: str, metadata: dict) -> list[RawEpisode]:
    # Step 1: Parse PDF to markdown
    converter = DocumentConverter()
    doc = converter.convert(contract_pdf_path)
    markdown = doc.document.export_to_markdown()
    
    # Step 2: Semantic chunking (per section, NOT fixed size)
    sections = split_by_heading(markdown, min_section_length=200)
    
    # Step 3: 每個 section 變 episode，加 metadata header
    episodes = []
    for section_idx, section in enumerate(sections):
        enriched_content = f"""
[Contract Metadata]
Contract ID: {metadata['contract_id']}
Vendor: {metadata['vendor_name']} (code: {metadata['vendor_code']})
Contract Type: {metadata['contract_type']}
Valid: {metadata['valid_from']} to {metadata['valid_to']}
Section: {section['heading']}

[Section Content]
{section['content']}
        """.strip()
        
        episodes.append(RawEpisode(
            name=f"contract_{metadata['contract_id']}_section_{section_idx}",
            content=enriched_content,
            source=EpisodeType.text,
            source_description=f"Contract PDF: {metadata['contract_id']}",
            reference_time=datetime.fromisoformat(metadata['valid_from']),
        ))
    
    return episodes
```

**Chunking 3 原則**：
1. 唔好 fixed-size chunk（會斷 semantic boundary）
2. 按 document structure 切（章節、條款、表格）
3. 每 chunk 都包含 structured metadata header（**極重要**）

### 2.4 Category D - Conversational

```python
async def prepare_email_thread(thread: dict) -> list[RawEpisode]:
    conversation_body = "\n\n".join([
        f"{msg['from']} ({msg['date']}): {msg['body']}"
        for msg in thread['messages']
    ])
    
    return [RawEpisode(
        name=f"email_thread_{thread['thread_id']}",
        content=conversation_body,
        source=EpisodeType.message,
        source_description=f"Email thread: {thread['subject']}",
        reference_time=datetime.fromisoformat(thread['first_message_date']),
    )]
```

---

## 五、Multimodal Document 處理（圖、表、PPT）

### 3-Layer 策略

```
Layer 1: Structured Document Parser
  Docling / Granite-Docling → 抽 text + tables + figures + reading order

Layer 2: Element-Specific Handlers
  Text → 直接入 Graphiti
  Tables → Markdown / JSON
  Simple figures → VLM caption
  Complex figures → VLM structured description
  Abstract diagrams → hybrid approach

Layer 3: Graphiti Ingestion
  Enriched episodes + structured metadata + VLM description
```

### Format 支援

| Format | Tool | Tables | Figures | Charts | Order |
|--------|------|--------|---------|--------|-------|
| PDF | Docling | ✅ 優 | ✅ 優 | ⚠️ Good | ✅ 優 |
| DOCX | Docling | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ |
| PPTX | Docling | ✅ | ✅ | ⚠️ Mixed | ✅ |
| XLSX | Docling/pandas | ✅ 原生 | — | ⚠️ Limited | N/A |
| Scanned PDF | Docling + OCR | ⚠️ | ⚠️ | ❌ | ⚠️ |

**推薦**：Docling (IBM, Linux Foundation, MIT) + Granite-Docling VLM

### 處理 Table

```python
for table in doc.tables:
    table_md = table.export_to_markdown()
    await graphiti.add_episode(
        name=f"table_{doc_id}_{table.page_no}",
        episode_body=f"""
[Table from {doc_id}, page {table.page_no}]
Caption: {table.caption or 'N/A'}

{table_md}
        """,
        source=EpisodeType.text,
    )
```

**注意**：保留 Markdown table format，LLM 對呢個 format entity extraction 最準

### 處理 Simple Figure

```python
for picture in doc.pictures:
    vlm_description = await claude_vision.describe(
        image=picture.image,
        prompt="""Describe this figure for knowledge graph extraction:
1. Type? (chart/diagram/photo/screenshot/flowchart)
2. What entities/concepts appear?
3. What relationships shown?
4. Numeric data visible?
Output as structured JSON."""
    )
    
    await graphiti.add_episode(
        name=f"figure_{doc_id}_{picture.page_no}",
        episode_body=f"""
[Figure from {doc_id}, page {picture.page_no}]
Original caption: {picture.caption}
VLM description: {vlm_description}
Context: {surrounding_text}
        """,
        source=EpisodeType.text,
    )
```

### 處理 PPT

**關鍵 insight**：每個 slide 通常表達 complete idea，per-slide episode。**Speaker notes 經常比 slide text 更有信息量**。

```python
for slide_idx, slide in enumerate(doc.pages):
    slide_text = extract_text_from_slide(slide)
    slide_tables = extract_tables_from_slide(slide)
    slide_figures = extract_figures_from_slide(slide)
    
    enriched_body = f"""
[Presentation: {doc_name}]
[Slide {slide_idx + 1}: {slide_title}]

Text content:
{slide_text}

Tables:
{format_tables(slide_tables)}

Figures:
{await describe_figures_with_vlm(slide_figures)}

Speaker notes:
{slide.speaker_notes}
    """
    
    await graphiti.add_episode(
        name=f"slide_{doc_id}_{slide_idx}",
        episode_body=enriched_body,
    )
```

### 抽象圖嘅 3-Level 策略

```
Level A: 標準化抽象圖（Architecture, Flow, Org chart）
  → VLM + specialized prompt
  → Success rate 70-85%

Level B: 半結構化（Mind maps, Conceptual diagrams）
  → VLM + 人工 validation
  → Success rate 50-70%

Level C: 藝術化/抽象表達（隨手畫、創意 sketch）
  → 降級：只記錄「有呢張圖」+ 原 context
  → 靠 surrounding text
```

**實戰 Strategy**：

```python
async def handle_abstract_diagram(figure, surrounding_context: str):
    # Step 1: Classify
    diagram_type = await vlm_classify(figure.image)
    
    # Step 2: 按 type 用不同 prompt
    if diagram_type == "architecture":
        description = await vlm_extract(
            figure.image,
            prompt=ARCHITECTURE_DIAGRAM_PROMPT,
        )
    elif diagram_type == "flowchart":
        description = await vlm_extract(
            figure.image,
            prompt=FLOWCHART_PROMPT,
        )
    elif diagram_type in ("conceptual", "abstract", "unknown"):
        description = f"""
Figure type: {diagram_type}
Generic description: {await vlm_describe_generic(figure.image)}
Surrounding context: {surrounding_context}
Original artifact: {figure.artifact_url}

[HUMAN_REVIEW_SUGGESTED]
        """
    
    return description
```

**3 個 Principle**：
1. **永遠保留 original artifact**（Azure Blob URL pointer）
2. **接受 imperfect extraction**，靠 surrounding context 補救
3. **`[HUMAN_REVIEW_SUGGESTED]` tag** 俾 data steward periodic review

---

## 六、Stage 3 - Ingestion Execution

### 2 種 Mode Trade-off

| Mode | API | 用途 | Pros | Cons |
|------|-----|------|------|------|
| **Bulk** | `add_episode_bulk()` | Empty graph / historical | 快 10-100x | ❌ **冇 edge invalidation** |
| **Incremental** | `add_episode()` | Real-time | ✅ Full temporal reasoning | 慢 |

**黃金規則**：
- Historical backfill → bulk
- Real-time operations → incremental
- 歷史 data 有 contradicting facts → **必須 incremental 按時間順序**

### Bulk Ingestion

```python
async def bulk_ingest_historical(graphiti, episodes: list[RawEpisode]):
    # 必須按 reference_time 排序
    episodes_sorted = sorted(episodes, key=lambda e: e.reference_time)
    
    BATCH_SIZE = 50
    total = len(episodes_sorted)
    
    for i in range(0, total, BATCH_SIZE):
        batch = episodes_sorted[i:i+BATCH_SIZE]
        try:
            await graphiti.add_episode_bulk(
                batch,
                entity_types=entity_types,
                edge_types=edge_types,
                edge_type_map=edge_type_map,
            )
            print(f"✓ Batch {i//BATCH_SIZE + 1}/{(total-1)//BATCH_SIZE + 1}")
        except Exception as e:
            await log_failed_batch(batch, str(e))
```

**實戰 tips**：
- Batch 50 個 episode 係 sweet spot
- 必須 handle partial failure
- 用 `group_id` 分 tenant / department

### Incremental Ingestion

```python
async def ingest_new_invoice(graphiti, invoice_data: dict):
    episode = await prepare_invoice(invoice_data)
    
    result = await graphiti.add_episode(
        name=episode.name,
        episode_body=episode.content,
        source=episode.source,
        source_description=episode.source_description,
        reference_time=episode.reference_time,
        entity_types=entity_types,
        edge_types=edge_types,
        edge_type_map=edge_type_map,
        group_id="rapo_finance",
    )
    
    # Graphiti 自動:
    # 1. Extract entities
    # 2. Extract relationships
    # 3. Resolve against existing entities
    # 4. Check edge invalidation
    # 5. Update embeddings + indices
```

### 3 種 Trigger Pattern

```python
# A. Webhook-based (real-time)
@app.post("/webhooks/sap/invoice")
async def sap_invoice_webhook(invoice_data: InvoiceIDoc):
    await ingest_new_invoice(graphiti, invoice_data.dict())

# B. Scheduled batch (nightly)
@celery.task(bind=True, max_retries=3)
async def nightly_contract_sync(self):
    updated = await fetch_contracts_modified_since_last_run()
    episodes = []
    for contract in updated:
        episodes.extend(await prepare_contract(contract.pdf, contract.metadata))
    await bulk_ingest_historical(graphiti, episodes)

# C. MCP Server (通用)
@mcp_server.tool
async def ingest_document(doc_path: str, doc_type: str, metadata: dict) -> dict:
    episodes = await PREPARE_DISPATCHER[doc_type](doc_path, metadata)
    result = await graphiti.add_episode_bulk(episodes)
    return {"ingested_episodes": len(episodes), "status": "ok"}
```

---

## 七、Stage 4 - Post-Ingestion Processing

### Entity Resolution Review

Graphiti dedup 準確率 85-90%，10-15% 需 human review：

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
```

### Community Building

```python
# 每日或每週跑
async def refresh_communities():
    await graphiti.build_communities()
    # 創建 community summary nodes，幫 high-level sensemaking
```

**Schedule**：production 通常每 6-24 小時 rebuild 一次

---

## 八、Stage 5 - Ongoing Operations

### 持續更新嘅 3 種 Trigger

```
     PUSH              POLL              STREAM
   (Event)           (Batch)           (CDC/WAL)
     │                 │                 │
  Webhook         Scheduled Job     Kafka/Event Hub
     └─────────────────┴─────────────────┘
                       ↓
              n8n/Celery Orchestration
                       ↓
              Graphiti Incremental Ingest
```

### Per-source Update Strategy

| Source | Trigger | Frequency | Pattern |
|--------|---------|-----------|---------|
| SAP Invoice | IDoc webhook | Real-time | New episode per event |
| ServiceNow Incident | Webhook on update | Real-time | New episode per status change |
| SharePoint Contract | Graph API notification | Near-real-time | Re-parse + re-ingest |
| Vendor Master | Nightly ETL | T+1 | Diff-based update |
| Email/Teams | Graph API subscription | Streaming | Per-message |
| Slack | Events API | Streaming | Per-message |
| HR/PeopleSoft | BAPI dump | Weekly | Diff-based |

### Graphiti Bitemporal 優勢

**場景**：Tom 2024 係 Finance Analyst → 2025 Manager → 2026 Senior Manager

Graphiti 自動處理：
```
Edge 1: Tom --HELD_POSITION--> Finance Analyst
        valid_from: 2024-01-01
        valid_to:   2025-06-30  ← 自動 invalidate

Edge 2: Tom --HELD_POSITION--> Finance Manager
        valid_from: 2025-07-01
        valid_to:   2026-03-31  ← 自動 invalidate

Edge 3: Tom --HELD_POSITION--> Senior Manager
        valid_from: 2026-04-01
        valid_to:   NULL  ← 現時
```

Query「Tom 而家」或「Tom 2025-12」，Graphiti 自動 temporal filter。**LongMemEval +18.5% accuracy，唔係 marketing**

### 5 種 Update Operations

```python
# 1. New fact addition
await graphiti.add_episode(
    name="new_invoice_2026_04_17",
    episode_body="RICOH HK 2026-04-17 submitted INV-2026-0417...",
    reference_time=datetime(2026, 4, 17),
)

# 2. Fact update / contradiction
await graphiti.add_episode(
    name="contract_amendment_2026_04",
    episode_body="Contract C2024-117 extended to 2027-12-31",
    reference_time=datetime(2026, 4, 15),
)
# Graphiti 自動 invalidate 舊 edge + create 新 edge

# 3. Document update
async def update_contract_document(contract_id: str, new_pdf_path: str):
    new_episodes = await prepare_contract(new_pdf_path, metadata)
    
    # Mark 舊版本 superseded
    await graphiti.add_episode(
        name=f"contract_{contract_id}_update_marker",
        episode_body=f"Contract {contract_id} updated to v{new_version}...",
        reference_time=datetime.now(),
    )
    
    # Ingest 新版本
    for ep in new_episodes:
        await graphiti.add_episode(
            name=ep.name,
            episode_body=ep.content,
            reference_time=new_version_effective_date,
        )

# 4. Delete / retract (GDPR)
await graphiti.add_episode(
    name="retraction_2026_04_17",
    episode_body="RETRACTION: 'V0099 has 30-day payment terms' incorrect. Correct: 60 days.",
    reference_time=datetime.now(),
)

# 5. Schema evolution
class Asset(BaseModel):
    asset_id: str
    asset_type: str

entity_types["Asset"] = Asset
edge_type_map[("Employee", "Asset")] = ["Uses"]
# 新 episode 用新 schema；舊 episode 不受影響
```

### 4 種 Change Detection Pattern

```python
# A. Source-side hash (最穩陣)
async def nightly_sharepoint_sync():
    for doc in await sharepoint.list_documents():
        last_hash = await db.get_last_ingested_hash(doc.id)
        if doc.etag != last_hash:
            content = await sharepoint.download(doc.id)
            episodes = await prepare_contract(content, doc.metadata)
            await bulk_ingest(graphiti, episodes)
            await db.save_ingestion_log(doc.id, doc.etag)

# B. Timestamp-based delta
async def hourly_incident_sync():
    last_sync = await db.get_last_sync_time("servicenow_incidents")
    new_incidents = await servicenow.query(
        f"sys_updated_on > {last_sync}"
    )
    for inc in new_incidents:
        await graphiti.add_episode(...)

# C. CDC (最 real-time)
async for change_event in kafka_consumer.consume("sap.invoices"):
    if change_event.operation in ("CREATE", "UPDATE"):
        await graphiti.add_episode(
            content=change_event.after_image,
            reference_time=change_event.commit_time,
        )
    elif change_event.operation == "DELETE":
        await graphiti.add_episode(
            content=f"Record {change_event.key} deleted",
            reference_time=change_event.commit_time,
        )

# D. Event-driven webhook
@app.post("/webhook/servicenow/incident_updated")
async def on_incident_update(event: IncidentEvent):
    await graphiti.add_episode(
        name=f"incident_{event.sys_id}_update_{event.sys_updated_on}",
        episode_body=json.dumps({
            "incident_id": event.sys_id,
            "state": event.state,
        }),
        reference_time=event.sys_updated_on,
    )
```

---

## 九、Monitoring Metrics

| Metric | Healthy Range | Alert |
|--------|---------------|-------|
| Ingestion latency p95 | <5s | >30s |
| Error rate | <1% | >5% |
| Entity dedup rate | 10-30% | <5% or >50% |
| LLM cost per episode | $0.01-0.05 | >$0.10 |
| Node growth | Linear | Sudden spike |
| Neo4j query p95 | <500ms | >2s |
| Community refresh | <10min/100k | >30min |

---

## 十、4 個常見 Pitfall

### Pitfall 1：一次過 ingest 全公司 data
**症狀**：Day 1 想 ingest HR + Finance + IT + SCM 全部
**解法**：Vertical slice — 1 department + 1 use case 先做完

### Pitfall 2：Chunking 太粗或太幼
- 太粗：context overflow、miss entity
- 太幼：dedup 爆炸、成本暴增、temporal relationship 丟失

**Sweet spot**：200-2000 tokens per episode，按 semantic boundary

### Pitfall 3：冇 metadata contextual enrichment

Raw：`"clause 4.3: surcharge shall not exceed 8%..."`

Enriched：
```
[Contract: C2024-117 | Vendor: RICOH HK | Type: MSA | Valid: 2025-01 to 2026-12]
clause 4.3: surcharge shall not exceed 8%...
```

**後者 entity extraction 質素高 2-3 倍**

### Pitfall 4：冇分 tenant / group_id

**症狀**：Finance 同 IT memory 混埋
**解法**：
```python
# Ingest with scope
await graphiti.add_episode(..., group_id="rapo_finance")

# Search within scope
await graphiti.search(query, group_ids=["rapo_finance"])
```

---

## 十一、Monthly Health Check

```python
async def monthly_health_check():
    # 1. Entity 數量突增檢查
    growth_rate = await check_entity_growth_rate()
    
    # 2. Orphan entities
    orphans = await graphiti.driver.execute_query(
        "MATCH (n) WHERE NOT (n)--() RETURN count(n) AS orphan_count"
    )
    
    # 3. Stale facts
    stale = await find_stale_facts(months=6)
    
    # 4. Schema coverage
    coverage = await check_schema_coverage()
    
    # → Report 俾 data steward
```

---

## 十二、對 IPA Platform 嘅 Integration

```
┌───────────────────────────────────────────────────────────┐
│                     IPA Platform                          │
│                                                           │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ Orchestrator │──→│ Graphiti MCP │──→│   Neo4j      │ │
│  │   Agent      │   │    Server    │   │   (KG)       │ │
│  └──────────────┘   └──────────────┘   └──────────────┘ │
│         ↑                    ↑                           │
│         │                    │ ingest_episode (from):   │
│         │                    │   - n8n webhook           │
│         │                    │   - SAP MCP server        │
│         │                    │   - SharePoint sync       │
│         │                    │   - ServiceNow webhook    │
│         │                    │   - Email MCP             │
│         │                                                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │      Existing 8 MCP Servers (reusable)             │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

**新建 components**：
1. **Graphiti MCP Server**（~1 週）— Wrap search / resolve / ingest 做 MCP tools
2. **Ingestion Pipeline Workers**（~2-3 週）— Celery / n8n workflow
3. **Schema Registry**（~1 週）— Centralized Pydantic definitions + version control
4. **Data Steward UI**（~3 週）— Duplicate review + schema proposals + monitoring

---

## 十三、Phase 1 Timeline（8-10 週）

```
Week 1-2: Foundation
  □ Neo4j deployment
  □ Graphiti + LLM integration
  □ Schema v1 (5 entity types, 3 edge types)
  □ Source inventory spreadsheet

Week 3-4: Vendor Master + Contract
  □ Bulk load vendor master
  □ Contract ingestion pipeline
  □ Entity resolution review
  □ Initial query testing

Week 5-6: Real-time Integration
  □ SAP invoice webhook
  □ ServiceNow incident webhook
  □ Graphiti MCP server

Week 7-8: IPA Orchestrator Integration
  □ Function tools (search_kg, resolve_entity)
  □ Active retrieval pattern
  □ End-to-end test (freight invoice)

Week 9-10: Production Hardening
  □ Monitoring & alerting
  □ Backup & DR
  □ Schema evolution process
  □ Data steward UI MVP
```

---

## Bottom Line

**總共 Phase 1：8-10 週 deliver 可 production run 嘅 ingestion pipeline**

一旦 work 起來，加新 source（HR、Procurement、IT Ops）marginal cost ~1-2 週。

**最 critical 成功要素**：
1. Ontology schema design 做得好（Week 1-2 唔好趕）
2. Entity resolution review workflow 建立得早
3. Group_id / tenant isolation 一開始 design 對
4. Monitoring + evaluation harness 平行 build
5. 接受 ingestion pipeline 係 **living system**，唔係 one-time project

---

*整理自 2026-04 系列討論*
