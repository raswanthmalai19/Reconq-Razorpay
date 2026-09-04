import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Component, useState } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Decisions from './pages/Decisions';
import Exceptions from './pages/Exceptions';
import Anomalies from './pages/Anomalies';
import AuditLog from './pages/AuditLog';
import Copilot from './components/Copilot';

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error('ReconQ crashed:', error, info); }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, maxWidth: 560 }}>
          <h2 style={{ color: 'var(--accent-red)', marginBottom: 8 }}>Something went wrong</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 16 }}>
            {this.state.error?.message || 'An unexpected error occurred while rendering this page.'}
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ padding: '8px 16px', borderRadius: 7, background: 'var(--accent-blue)', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const [results, setResults] = useState(null);
  const [runId, setRunId] = useState(null);
  const [copilotOpen, setCopilotOpen] = useState(false);

  return (
    <BrowserRouter>
      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-primary)' }}>
        <Sidebar onToggleCopilot={() => setCopilotOpen(o => !o)} copilotOpen={copilotOpen} hasResults={!!results} results={results} />
        <main className="rq-main" style={{ flex: 1, overflowY: 'auto', padding: '28px 32px', minWidth: 0 }}>
          <div style={{ maxWidth: 1140 }}>
            <ErrorBoundary>
              <Routes>
                <Route path="/"           element={<Dashboard  results={results} setResults={setResults} runId={runId} setRunId={setRunId} />} />
                <Route path="/decisions"  element={<Decisions  results={results} runId={runId} />} />
                <Route path="/exceptions" element={<Exceptions results={results} runId={runId} />} />
                <Route path="/anomalies"  element={<Anomalies  results={results} />} />
                <Route path="/audit"      element={<AuditLog   runId={runId} />} />
              </Routes>
            </ErrorBoundary>
          </div>
        </main>
        {copilotOpen && (
          <Copilot runId={runId} onClose={() => setCopilotOpen(false)} />
        )}
      </div>
    </BrowserRouter>
  );
}
