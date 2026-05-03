/**
 * File: frontend/src/pages/governance/index.tsx
 * Purpose: Governance page route container — nests /governance/approvals (Sprint 53.5 US-1).
 * Category: Frontend / pages / governance
 * Scope: Phase 53 / Sprint 53.5 US-1
 *
 * Modification History:
 *   - 2026-05-04: Wire ApprovalsPage at /approvals (Sprint 53.5 US-1).
 *   - 2026-04-29: Initial placeholder (Sprint 49.1).
 */

import { Link, Navigate, Route, Routes } from "react-router-dom";

import { ApprovalsPage } from "../../features/governance/components/ApprovalsPage";

function GovernanceIndex() {
  return (
    <div style={{ padding: "1.5rem 2rem", fontFamily: "system-ui, sans-serif" }}>
      <h2 style={{ marginTop: 0 }}>Governance</h2>
      <ul>
        <li>
          <Link to="approvals">Pending approvals</Link> — review HITL requests
        </li>
      </ul>
      <p style={{ color: "#888", fontSize: "0.9rem" }}>
        Audit log + risk policy management land in subsequent sprints.
      </p>
    </div>
  );
}

export default function GovernancePage() {
  return (
    <Routes>
      <Route index element={<GovernanceIndex />} />
      <Route path="approvals" element={<ApprovalsPage />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  );
}
