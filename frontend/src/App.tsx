import { Link, Route, Routes } from "react-router-dom";
import ChatV2Page from "./pages/chat-v2";
import GovernancePage from "./pages/governance";
import VerificationPage from "./pages/verification";

// Sprint 49.1 placeholder router. Real navigation / layout shell
// lands in Phase 50.2 (chat-v2 main flow) and is extended each phase.
function Home() {
  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>IPA Platform V2</h1>
      <p>
        <strong>Status:</strong> Phase 49 Foundation, Sprint 49.1 — frontend skeleton only.
      </p>
      <p>Pages currently registered (placeholders):</p>
      <ul>
        <li>
          <Link to="/chat-v2">/chat-v2</Link> — Phase 50.2 main flow
        </li>
        <li>
          <Link to="/governance">/governance</Link> — Phase 53.3 HITL UI
        </li>
        <li>
          <Link to="/verification">/verification</Link> — Phase 54.1 verifier panel
        </li>
      </ul>
      <p>
        Backend health: <code>GET /api/v1/health</code> (proxied to localhost:8001)
      </p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/chat-v2/*" element={<ChatV2Page />} />
      <Route path="/governance/*" element={<GovernancePage />} />
      <Route path="/verification/*" element={<VerificationPage />} />
    </Routes>
  );
}
