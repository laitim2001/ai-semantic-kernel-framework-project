# Project Documentation Structure

This project follows the **BMAD Method (Build-Measure-Analyze-Deploy)** workflow for structured product development.

## 📁 Directory Structure

### Phase 0: Discovery 🔍
**Location:** `00-discovery/`

Initial exploration and ideation phase to understand the problem space and define the product vision.

- **`brainstorming/`** - Brainstorming session outputs
  - Session results and detailed exploration documents
  - Multiple brainstorming techniques (Mind Mapping, What-If, First Principles, SCAMPER)
  
- **`product-brief/`** - Strategic product planning
  - Product vision and positioning
  - Market analysis and competitive landscape
  - High-level requirements and success criteria

**Key Deliverables:**
- ✅ Brainstorming Session Results (2025-11-14)
- ⏭️ Product Brief

---

### Phase 1: Planning 📋
**Location:** `01-planning/`

Detailed planning and requirements definition phase.

- **`prd/`** - Product Requirements Document
  - Detailed feature specifications
  - User stories and acceptance criteria
  - Technical requirements
  - Success metrics and KPIs
  
- **`design/`** - UX/UI Design (if applicable)
  - User flows and wireframes
  - UI mockups and prototypes
  - Design system guidelines

**Key Deliverables:**
- ⏭️ PRD (Product Requirements Document)
- ⏭️ Design Documents (conditional)

---

### Phase 2: Solutioning 🏗️
**Location:** `02-solutioning/`

Architecture and technical design phase.

- **`architecture/`** - System Architecture
  - Architecture Decision Records (ADRs)
  - System design diagrams
  - Technology stack decisions
  - Integration patterns
  
- **`test-design/`** - Test Strategy (recommended)
  - Test plan and strategy
  - Test cases and scenarios
  - Quality assurance approach

**Key Deliverables:**
- ⏭️ Architecture Document
- ⏭️ Test Design (recommended)
- ⏭️ Solutioning Gate Check

---

### Phase 3: Implementation 🚀
**Location:** `03-implementation/`

Agile implementation phase with sprint-based execution.

- **`sprints/`** - Sprint Planning and Tracking
  - Sprint plans and goals
  - Sprint retrospectives
  - Implementation progress tracking

**Key Deliverables:**
- ⏭️ Sprint Plans
- ⏭️ Implementation Artifacts

---

## 📄 Root Documentation Files

- **`bmm-workflow-status.yaml`** - Tracks progress through BMAD workflow phases
- **`sprint-artifacts/`** - Sprint-specific deliverables and artifacts

---

## 🔄 Workflow Progression

```
Discovery (Phase 0)
  └─ Brainstorm → Product Brief
       ↓
Planning (Phase 1)
  └─ PRD → Design (if needed)
       ↓
Solutioning (Phase 2)
  └─ Architecture → Test Design → Gate Check
       ↓
Implementation (Phase 3)
  └─ Sprint Planning → Development
```

---

## 📌 Current Status

**Project:** Enterprise AI Agent Framework  
**Track:** BMAD Method (Greenfield)  
**Current Phase:** Phase 0 - Discovery  
**Last Updated:** 2025-11-14

### Completed
- ✅ Workflow Initialization
- ✅ Brainstorming Session (Progressive Flow: 4 techniques)

### In Progress
- 🔄 Document Restructuring

### Next Steps
- ⏭️ Product Brief Creation
- ⏭️ PRD Development

---

## 🔗 Quick Links

- [Workflow Status](./bmm-workflow-status.yaml)
- [Brainstorming Results](./00-discovery/brainstorming/README.md)
- [Product Brief](./00-discovery/product-brief/) (Coming soon)

---

**Generated:** 2025-11-14  
**Method:** BMAD Method v6.0.0-alpha.9
