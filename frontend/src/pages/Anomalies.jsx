import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, AlertTriangle, TrendingDown, Clock, Copy, ChevronDown, ChevronUp } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge, { SEVERITY_STYLES } from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';

const TYPE_ICONS = {
  'Fee Overcharge':     TrendingDown,
  'Missing Settlement': ShieldAlert,
  'Duplicate Pattern':  Copy,
  'Timing Delay':       Clock,
};

const fmtRupees = v => {
  if (!v && v !== 0) return '—';
  if (v >= 100000) return `₹${(v / 100000).toFixed(2)}L`;
  if (v >= 1000)   return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${v.toFixed(0)}`;
};

function AnomalyCard({ anomaly }) {
  const [expanded, setExpanded] = useState(false);
  const sev = SEVERITY_STYLES[anomaly.severity] || SEVERITY_STYLES.MEDIUM;
  const Icon = TYPE_ICONS[anomaly.anomaly_type] || AlertTriangle;

  return (
    <Card hover>
      <div style={{ padding: '14px 18px', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 8, background: sev.bg, border: `1px solid ${sev.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon size={16} color={sev.color} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{anomaly.anomaly_type}</span>
            <Badge label={anomaly.severity} styleMap={SEVERITY_STYLES} size="sm" />
          </div>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{anomaly.description}</p>
          <div style={{ marginTop: 8, display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Impact: <strong style={{ color: 'var(--accent-red)' }}>{fmtRupees(anomaly.estimated_impact_rupees)}</strong>
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {anomaly.affected_records?.length || 0} records affected
            </span>
          </div>
        </div>
        {anomaly.affected_records?.length > 0 && (
          <button onClick={() => setExpanded(e => !e)} className="rq-btn" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: 'var(--text-muted)', flexShrink: 0 }}>
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        )}
      </div>
      {expanded && anomaly.affected_records?.length > 0 && (
        <div className="rq-fade-in" style={{ borderTop: '1px solid var(--border)', padding: '10px 18px', background: 'var(--bg-subtle)' }}>
          <p style={{ margin: '0 0 6px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Affected records</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {anomaly.affected_records.slice(0, 20).map(id => (
              <span key={id} style={{ fontSize: 11, fontFamily: 'monospace', padding: '2px 7px', background: '#fff', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-secondary)' }}>
                {id}
              </span>
            ))}
            {anomaly.affected_records.length > 20 && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)', padding: '2px 7px' }}>
                +{anomaly.affected_records.length - 20} more
              </span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function Anomalies({ results }) {
  const navigate = useNavigate();

  if (!results) return (
    <EmptyState icon={ShieldAlert} title="No results yet" actionLabel="Go to Dashboard" onAction={() => navigate('/')} />
  );

  const anomalies = results.anomalies || [];
  const lr = results.leakage_report;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: -0.3 }}>Anomaly Detection</h2>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-secondary)' }}>Revenue leakage and settlement irregularities</p>
      </div>

      {/* Summary strip */}
      {lr && (
        <Card padding="16px 20px">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 14 }}>
            {[
              { label: 'Total at Risk', value: fmtRupees(lr.total_leakage_rupees), color: 'var(--accent-red)' },
              { label: 'Fee Overcharges', value: fmtRupees(lr.by_category?.['Fee Overcharge'] || 0), color: 'var(--accent-yellow)' },
              { label: 'Missing Settlements', value: fmtRupees(lr.by_category?.['Missing Settlement'] || 0), color: 'var(--accent-red)' },
              { label: 'Timing Delays', value: fmtRupees(lr.by_category?.['Timing Delay'] || 0), color: 'var(--text-secondary)' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color, letterSpacing: -0.5 }}>{value}</div>
              </div>
            ))}
          </div>
          {lr.recommendations?.length > 0 && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
              <p style={{ margin: '0 0 6px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Recommendations</p>
              <ul style={{ margin: 0, padding: '0 0 0 16px' }}>
                {lr.recommendations.map((r, i) => (
                  <li key={i} style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 3, lineHeight: 1.5 }}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Anomaly cards */}
      {anomalies.length === 0 ? (
        <Card>
          <EmptyState icon={ShieldAlert} tone="success" title="No anomalies detected" subtitle="Your settlement data looks clean." />
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {anomalies.map((a, i) => <AnomalyCard key={i} anomaly={a} />)}
        </div>
      )}
    </div>
  );
}
