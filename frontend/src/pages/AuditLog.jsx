import { useEffect, useState, useCallback } from 'react';
import { Download, ClipboardList, RefreshCw } from 'lucide-react';
import { getAuditLog } from '../api/client';
import Badge, { EVENT_STYLES } from '../components/ui/Badge';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import { SkeletonRows } from '../components/ui/Skeleton';

const EVENT_TYPES = ['ALL', 'EXACT_MATCH', 'DECISION', 'GROUP_MATCH', 'OVERRIDE'];

function parsePayload(p) {
  if (!p) return null;
  try { return typeof p === 'string' ? JSON.parse(p) : p; } catch { return null; }
}

function PayloadPreview({ payload }) {
  const p = parsePayload(payload);
  if (!p) return <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>—</span>;
  const keys = ['invoice', 'settlement', 'conf', 'status', 'decision'];
  const parts = keys.filter(k => p[k] !== undefined).map(k => (
    <span key={k} style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#f4f4f5', border: '1px solid var(--border)', color: 'var(--text-secondary)', marginRight: 4 }}>
      {k}: {typeof p[k] === 'number' ? p[k].toFixed(3) : String(p[k]).slice(0, 20)}
    </span>
  ));
  return <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>{parts.length ? parts : <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{JSON.stringify(p).slice(0, 60)}…</span>}</div>;
}

function formatTs(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'medium' });
}

export default function AuditLog({ runId }) {
  const [logs, setLogs]             = useState([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [activeFilter, setFilter]   = useState('ALL');

  const load = useCallback(() => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    getAuditLog(runId)
      .then(setLogs)
      .catch(() => setError('Failed to load audit log.'))
      .finally(() => setLoading(false));
  }, [runId]);

  useEffect(() => { load(); }, [load]);

  const filtered = activeFilter === 'ALL' ? logs : logs.filter(l => l.event_type === activeFilter);

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `audit-log-${runId?.slice(0,8) || 'export'}.json`;
    a.click();
  };

  if (!runId) return (
    <EmptyState icon={ClipboardList} title="No audit log yet" subtitle="Run a reconciliation first to see the audit log." />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: -0.3 }}>Audit Log</h2>
          <p style={{ margin: '3px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>
            Run <span style={{ fontFamily: 'monospace' }}>{runId?.slice(0, 8)}</span>
          </p>
        </div>
        <Button icon={Download} onClick={handleDownload} disabled={!logs.length}>Download JSON</Button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
        {[
          { label: 'Total Events', value: logs.length, color: 'var(--text-primary)' },
          { label: 'System Events', value: logs.filter(l => l.actor === 'system').length, color: 'var(--accent-blue)' },
          { label: 'Human Overrides', value: logs.filter(l => l.event_type === 'OVERRIDE').length, color: 'var(--accent-yellow)' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 14px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color, letterSpacing: -0.5 }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {EVENT_TYPES.map(t => (
          <button key={t} onClick={() => setFilter(t)} className="rq-chip" style={{
            fontSize: 12, fontWeight: 500, padding: '5px 10px', borderRadius: 6,
            border: `1px solid ${activeFilter === t ? 'var(--accent-blue)' : 'var(--border)'}`,
            background: activeFilter === t ? 'var(--accent-blue-light)' : '#fff',
            color: activeFilter === t ? 'var(--accent-blue)' : 'var(--text-secondary)',
            cursor: 'pointer',
          }}>
            {t.replace(/_/g, ' ')}
            {t !== 'ALL' && <span style={{ marginLeft: 5, fontSize: 10, color: 'var(--text-muted)' }}>({logs.filter(l => l.event_type === t).length})</span>}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 10 }}>
          <SkeletonRows rows={6} cols={5} />
        </div>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 16, color: 'var(--accent-red)', fontSize: 13, background: 'var(--accent-red-light)', border: '1px solid #fecaca', borderRadius: 8 }}>
          {error}
          <Button size="sm" variant="danger" icon={RefreshCw} onClick={load}>Retry</Button>
        </div>
      ) : (
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border)' }}>
                {['Timestamp', 'Record ID', 'Actor', 'Event', 'Payload'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '9px 12px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((log, i) => (
                <tr key={i} className="rq-row" style={{ borderTop: '1px solid var(--border-light)' }}>
                  <td style={{ padding: '8px 12px', fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{formatTs(log.timestamp)}</td>
                  <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 11, color: 'var(--text-primary)', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.record_id || '—'}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{ fontSize: 11, padding: '2px 7px', borderRadius: 4, background: log.actor === 'system' ? '#f4f4f5' : 'var(--accent-blue-light)', color: log.actor === 'system' ? 'var(--text-muted)' : 'var(--accent-blue)', border: `1px solid ${log.actor === 'system' ? 'var(--border)' : '#bfdbfe'}`, fontWeight: 500 }}>
                      {log.actor}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}><Badge label={log.event_type} styleMap={EVENT_STYLES} /></td>
                  <td style={{ padding: '8px 12px' }}><PayloadPreview payload={log.payload} /></td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={5} style={{ padding: 32, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>No events found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
