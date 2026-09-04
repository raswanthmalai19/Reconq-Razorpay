import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Decisions from './pages/Decisions';
import Exceptions from './pages/Exceptions';
import Anomalies from './pages/Anomalies';
import AuditLog from './pages/AuditLog';
import Copilot from './components/Copilot';

export default function App() {
  const [results, setResults] = useState(null);
  const [runId, setRunId] = useState(null);
  const [copilotOpen, setCopilotOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
        <Sidebar onToggleCopilot={() => setCopilotOpen(o => !o)} copilotOpen={copilotOpen} hasResults={!!results} />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <Routes>
            <Route path="/"           element={<Dashboard  results={results} setResults={setResults} runId={runId} setRunId={setRunId} />} />
            <Route path="/decisions"  element={<Decisions  results={results} runId={runId} />} />
            <Route path="/exceptions" element={<Exceptions results={results} runId={runId} />} />
            <Route path="/anomalies"  element={<Anomalies  results={results} />} />
            <Route path="/audit"      element={<AuditLog   runId={runId} />} />
          </Routes>
        </main>
        {copilotOpen && (
          <Copilot runId={runId} onClose={() => setCopilotOpen(false)} />
        )}
      </div>
    </BrowserRouter>
  );
}
