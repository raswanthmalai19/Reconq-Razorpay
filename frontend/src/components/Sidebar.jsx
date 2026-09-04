import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Table2, AlertTriangle, ShieldAlert, ScrollText } from 'lucide-react';

const NAV = [
  { name: 'Dashboard',  path: '/',           icon: LayoutDashboard },
  { name: 'Decisions',  path: '/decisions',  icon: Table2         },
  { name: 'Exceptions', path: '/exceptions', icon: AlertTriangle  },
  { name: 'Anomalies',  path: '/anomalies',  icon: ShieldAlert    },
  { name: 'Audit Log',  path: '/audit',      icon: ScrollText     },
];

export default function Sidebar({ onToggleCopilot, copilotOpen, hasResults }) {
  return (
    <aside
      className="flex flex-col shrink-0 w-52 h-screen overflow-y-auto py-6 px-3 border-r"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
    >
      {/* Brand */}
      <div className="px-3 mb-8">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)' }}>
            <span className="text-white text-xs font-black">R</span>
          </div>
          <div>
            <p className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>ReconQ</p>
            <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>v3.0 · Risk-Weighted</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5">
        <p className="text-[10px] font-semibold uppercase tracking-widest px-3 mb-2"
          style={{ color: 'var(--text-secondary)', opacity: 0.5 }}>Navigation</p>
        {NAV.map(({ name, path, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive ? 'active-nav' : ''
              }`
            }
            style={({ isActive }) => ({
              color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
              background: isActive ? 'rgba(59,130,246,0.1)' : 'transparent',
            })}
          >
            <Icon size={15} />
            {name}
          </NavLink>
        ))}
      </nav>

      {/* Copilot */}
      <div className="mt-4 border-t pt-4" style={{ borderColor: 'var(--border)' }}>
        <button
          onClick={onToggleCopilot}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            color: copilotOpen ? 'var(--accent-blue)' : 'var(--text-secondary)',
            background: copilotOpen ? 'rgba(59,130,246,0.1)' : 'transparent',
          }}
        >
          <span className="text-base">✦</span>
          Copilot
          {!hasResults && (
            <span className="text-[9px] px-1.5 py-0.5 rounded ml-auto"
              style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444' }}>
              Run first
            </span>
          )}
        </button>
        <p className="text-[9px] px-3 mt-2" style={{ color: 'var(--text-secondary)', opacity: 0.4 }}>
          Queries real DataFrames via Gemini function-calling
        </p>
      </div>

      {/* Honest limitations label */}
      <div className="mt-4 mx-1 rounded-lg p-2.5 border" style={{ borderColor: 'rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.04)' }}>
        <p className="text-[9px] font-semibold mb-1" style={{ color: '#ef4444' }}>Known Limitations</p>
        <p className="text-[9px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Sample data is synthetic (154 records). Copilot responses are LLM-generated drafts. Group-match capped at subset-size 4 for bounded runtime.
        </p>
      </div>
    </aside>
  );
}
