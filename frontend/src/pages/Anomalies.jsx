import { useNavigate } from 'react-router-dom';
import { ShieldAlert, AlertTriangle, TrendingDown, Clock, Copy, ChevronDown } from 'lucide-react';
import { useState } from 'react';

const SEVERITY_STYLES = {
  CRITICAL: { bg: 'rgba(239,68,68,0.15)',  text: '#ef4444', icon: ShieldAlert },
  HIGH:     { bg: 'rgba(239,68,68,0.1)',   text: '#f87171', icon: AlertTriangle },
  MEDIUM:   { bg: 'rgba(245,158,11,0.15)', text: '#f59e0b', icon: AlertTriangle },
  LOW:      { bg: 'rgba(59,130,246,0.1)',  text: '#60a5fa', icon: Clock },
};

const TYPE_ICONS = {
  'Fee Overcharge':     TrendingDown,
  'Missing Settlement': ShieldAlert,
  'Duplicate Pattern':  Copy,
  'Timing Delay':       Clock,
};

function AnomalyCard({ anomaly }) {
  const [expanded, setExpanded] = useState(false);
  const s = SEVERITY_STYLES[anomaly.severity] || SEVERITY_STYLES.LOW;
  const Icon = TYPE_ICONS[anomaly.anomaly_type] || AlertTriangle;

  return (
    <div className="rounded-xl border overflow-hidden transition-all" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-card)' }}>
      <div
        className="flex items-start gap-4 p-5 cursor-pointer hover:bg-white/[0.02]"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="p-2.5 rounded-lg mt-0.5" style={{ background: s.bg }}>
          <Icon size={18} style={{ color: s.text }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{anomaly.anomaly_type}</span>
            <span className="text-xs px-2 py-0.5 rounded-full font-semibold" style={{ background: s.bg, color: s.text }}>
              {anomaly.severity}
            </span>
          </div>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{anomaly.description}</p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-lg font-bold" style={{ color: s.text }}>
            ₹{anomaly.estimated_impact_rupees?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) || '0.00'}
          </div>
          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>estimated impact</div>
        </div>
        <ChevronDown
          size={16}
          className="shrink-0 mt-1 transition-transform"
          style={{ color: 'var(--text-secondary)', transform: expanded ? 'rotate(180deg)' : '' }}
        />
      </div>
      {expanded && (
        <div className="px-5 pb-5 border-t" style={{ borderColor: 'var(--border)' }}>
          <p className="text-xs font-semibold mt-4 mb-2" style={{ color: 'var(--text-secondary)' }}>
            AFFECTED RECORDS ({anomaly.affected_records?.length || 0})
          </p>
          <div className="flex flex-wrap gap-2">
            {(anomaly.affected_records || []).slice(0, 20).map(id => (
              <span key={id} className="text-xs font-mono px-2 py-1 rounded" style={{ background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>
                {id}
              </span>
            ))}
            {(anomaly.affected_records?.length || 0) > 20 && (
              <span className="text-xs px-2 py-1 rounded" style={{ background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>
                +{anomaly.affected_records.length - 20} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Anomalies({ results }) {
  const navigate = useNavigate();
  const anomalies = results?.anomalies || [];
  const leakage   = results?.leakage_report;

  if (!results) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>No results yet.</p>
      <button onClick={() => navigate('/')} className="px-4 py-2 rounded-lg text-sm font-medium" style={{ background: 'var(--accent-blue)', color: '#fff' }}>
        ← Go to Dashboard
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Anomaly Detection & Revenue Leakage</h2>
        <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
          Deterministic analysis of fee patterns, timing delays, duplicates, and missing settlements
        </p>
      </div>

      {/* Leakage summary */}
      {leakage && (
        <div className="rounded-xl border p-6" style={{ backgroundColor: 'rgba(239,68,68,0.05)', borderColor: 'rgba(239,68,68,0.3)' }}>
          <div className="flex items-center gap-3 mb-4">
            <ShieldAlert size={20} style={{ color: '#ef4444' }} />
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>Revenue Leakage Summary</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-5">
            <div>
              <div className="text-2xl font-bold" style={{ color: '#ef4444' }}>
                ₹{leakage.total_leakage_rupees?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) || '0.00'}
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Total at risk</div>
            </div>
            <div>
              <div className="text-2xl font-bold" style={{ color: '#f59e0b' }}>{leakage.anomaly_count || anomalies.length}</div>
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Anomalies found</div>
            </div>
            {Object.entries(leakage.by_category || {}).slice(0, 2).map(([cat, val]) => (
              <div key={cat}>
                <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                  ₹{val?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{cat}</div>
              </div>
            ))}
          </div>
          {leakage.recommendations?.length > 0 && (
            <div>
              <p className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>RECOMMENDATIONS</p>
              <ul className="space-y-1.5">
                {leakage.recommendations.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span style={{ color: '#f59e0b' }}>→</span>
                    <span style={{ color: 'var(--text-primary)' }}>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Anomaly cards */}
      {anomalies.length > 0 ? (
        <div className="space-y-3">
          {anomalies.map((a, i) => <AnomalyCard key={i} anomaly={a} />)}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed p-12 text-center" style={{ borderColor: 'var(--border)' }}>
          <ShieldAlert size={36} className="mx-auto mb-3 opacity-30" style={{ color: 'var(--text-secondary)' }} />
          <p className="font-semibold" style={{ color: 'var(--text-secondary)' }}>No anomalies detected</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)', opacity: 0.6 }}>Your reconciliation looks clean!</p>
        </div>
      )}
    </div>
  );
}
