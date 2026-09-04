import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Table2, AlertTriangle, ShieldAlert, ScrollText, MessageSquare } from 'lucide-react';

const NAV = [
  { to: '/',          label: 'Dashboard',  icon: LayoutDashboard, end: true },
  { to: '/decisions', label: 'Decisions',  icon: Table2 },
  { to: '/exceptions',label: 'Exceptions', icon: AlertTriangle },
  { to: '/anomalies', label: 'Anomalies',  icon: ShieldAlert },
  { to: '/audit',     label: 'Audit Log',  icon: ScrollText },
];

function dataSourceLabel(results) {
  if (!results) return null;
  if (results.razorpay_source === 'razorpay_live') return 'Razorpay API (Live)';
  return 'ERP / CSV Upload';
}

export default function Sidebar({ onToggleCopilot, copilotOpen, hasResults, results }) {
  const source = dataSourceLabel(results);

  return (
    <aside className="rq-sidebar" style={{
      width: 216, flexShrink: 0, height: '100vh',
      background: '#ffffff',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      transition: 'width 0.15s var(--ease)',
    }}>
      {/* Brand */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8, flexShrink: 0,
            background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
            boxShadow: '0 2px 6px rgba(37,99,235,0.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ color: '#fff', fontSize: 13, fontWeight: 700, letterSpacing: -0.5 }}>R</span>
          </div>
          <div className="rq-sidebar-label">
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: -0.3 }}>ReconQ</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>AI Finance Controller</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '10px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `rq-navlink${isActive ? ' active' : ''}`}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 9,
              padding: '7px 10px', borderRadius: 7,
              textDecoration: 'none', fontSize: 13, fontWeight: 500,
              color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
              background: isActive ? 'var(--accent-blue-light)' : 'transparent',
            })}
            title={label}
          >
            <Icon size={15} style={{ flexShrink: 0 }} />
            <span className="rq-sidebar-label">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Copilot toggle */}
      <div style={{ padding: '10px 10px 20px' }}>
        <button
          onClick={onToggleCopilot}
          className="rq-btn"
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 9,
            padding: '8px 10px', borderRadius: 7, border: '1px solid var(--border)',
            background: copilotOpen ? 'var(--accent-blue-light)' : '#fff',
            color: copilotOpen ? 'var(--accent-blue)' : 'var(--text-secondary)',
            fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}
        >
          <MessageSquare size={15} style={{ flexShrink: 0 }} />
          <div className="rq-sidebar-label" style={{ flex: 1, textAlign: 'left' }}>
            <div>Copilot</div>
            {!hasResults && (
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>Run reconciliation first</div>
            )}
          </div>
        </button>
        {source && (
          <div className="rq-sidebar-label" style={{ marginTop: 12, padding: '8px 10px', background: 'var(--bg-subtle)', borderRadius: 7, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
              Data source: <strong style={{ color: 'var(--text-secondary)' }}>{source}</strong><br />
              Copilot: Gemini primary · Groq fallback.
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
