import { useEffect, useState } from 'react';
import { Download, Filter, Loader2, ClipboardList } from 'lucide-react';
import { getAuditLog } from '../api/client';

const EVENT_TYPES = ['ALL', 'EXACT_MATCH', 'DECISION', 'GROUP_MATCH', 'OVERRIDE'];

function parsePayload(payloadJson) {
  try {
    return JSON.parse(payloadJson);
  } catch {
    return null;
  }
}

function PayloadPreview({ payloadJson, eventType }) {
  const p = parsePayload(payloadJson);
  if (!p) return <span style={{ color: 'var(--text-secondary)', fontSize: 12, fontFamily: 'monospace' }}>{String(payloadJson).slice(0, 60)}</span>;

  const fields = [];
  if (p.invoice_id)    fields.push({ label: 'invoice', value: p.invoice_id });
  if (p.settlement_id) fields.push({ label: 'settlement', value: p.settlement_id });
  if (p.confidence != null) fields.push({ label: 'conf', value: `${Math.round(p.confidence * 100)}%` });
  if (p.status)        fields.push({ label: 'status', value: p.status });
  if (p.decision)      fields.push({ label: 'decision', value: p.decision });

  if (fields.length === 0) {
    const raw = JSON.stringify(p);
    return <span style={{ color: 'var(--text-secondary)', fontSize: 12, fontFamily: 'monospace' }}>{raw.slice(0, 80)}{raw.length > 80 ? '…' : ''}</span>;
  }

  return (
    <span style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {fields.slice(0, 3).map(f => (
        <span key={f.label} style={{ fontSize: 11, fontFamily: 'monospace', background: 'var(--bg-secondary)', padding: '1px 7px', borderRadius: 4, color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--text-secondary)', opacity: 0.6 }}>{f.label}: </span>
          <span style={{ color: 'var(--text-primary)' }}>{f.value}</span>
        </span>
      ))}
    </span>
  );
}

function ActorBadge({ actor }) {
  const isSystem = actor === 'system';
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99,
      background: isSystem ? 'rgba(59,130,246,0.15)' : 'rgba(16,185,129,0.15)',
      color: isSystem ? 'var(--accent-blue)' : 'var(--accent-green)',
      border: `1px solid ${isSystem ? 'rgba(59,130,246,0.25)' : 'rgba(16,185,129,0.25)'}`,
    }}>
      {actor}
    </span>
  );
}

function EventPill({ type }) {
  const colors = {
    DECISION:    { bg: 'rgba(139,92,246,0.15)', color: '#a78bfa' },
    EXACT_MATCH: { bg: 'rgba(16,185,129,0.15)', color: '#10b981' },
    GROUP_MATCH: { bg: 'rgba(59,130,246,0.15)', color: 'var(--accent-blue)' },
    OVERRIDE:    { bg: 'rgba(245,158,11,0.15)', color: '#f59e0b' },
  };
  const c = colors[type] || { bg: 'rgba(107,114,128,0.15)', color: '#9ca3af' };
  return (
    <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 9px', borderRadius: 99, background: c.bg, color: c.color }}>
      {type}
    </span>
  );
}

function formatTs(ts) {
  if (!ts) return '—';
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
  if (isNaN(d)) return String(ts);
  return d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function AuditLog({ runId }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ALL');

  useEffect(() => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    setLogs([]);
    getAuditLog(runId)
      .then(data => {
        // API may return array directly or { entries: [...] }
        const entries = Array.isArray(data) ? data : (data?.entries ?? data?.logs ?? []);
        setLogs(entries);
      })
      .catch(err => {
        console.error('getAuditLog error:', err);
        setError('Failed to load audit log. Please try again.');
      })
      .finally(() => setLoading(false));
  }, [runId]);

  if (!runId) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 320, gap: 12 }}>
        <ClipboardList size={40} style={{ color: 'var(--text-secondary)', opacity: 0.3 }} />
        <p style={{ fontSize: 16, color: 'var(--text-secondary)' }}>Run a reconciliation to see the complete audit trail</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 320, gap: 12 }}>
        <Loader2 size={32} style={{ color: 'var(--accent-blue)', animation: 'spin 1s linear infinite' }} />
        <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>Fetching audit log…</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 320, gap: 10 }}>
        <p style={{ color: '#ef4444', fontSize: 14 }}>{error}</p>
      </div>
    );
  }

  const systemCount = logs.filter(l => l.actor === 'system').length;
  const humanCount  = logs.filter(l => l.actor !== 'system').length;

  const filtered = activeFilter === 'ALL'
    ? logs
    : logs.filter(l => l.event_type === activeFilter);

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${runId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>Audit Log</h1>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2, fontFamily: 'monospace' }}>Run: {runId}</p>
        </div>
        <button
          onClick={handleDownload}
          disabled={logs.length === 0}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
            borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: logs.length === 0 ? 'not-allowed' : 'pointer',
            background: 'var(--bg-secondary)', color: 'var(--text-primary)',
            border: '1px solid var(--border)', opacity: logs.length === 0 ? 0.5 : 1,
          }}
        >
          <Download size={14} /> Download JSON
        </button>
      </div>

      {/* Stats strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {[
          { label: 'Total Events', value: logs.length, color: 'var(--text-primary)' },
          { label: 'System Events', value: systemCount, color: 'var(--accent-blue)' },
          { label: 'Human Overrides', value: humanCount, color: 'var(--accent-green)' },
        ].map(s => (
          <div key={s.label} style={{ padding: '14px 18px', borderRadius: 10, background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Filter size={14} style={{ color: 'var(--text-secondary)' }} />
        {EVENT_TYPES.map(t => (
          <button
            key={t}
            onClick={() => setActiveFilter(t)}
            style={{
              fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 99, cursor: 'pointer',
              background: activeFilter === t ? 'var(--accent-blue)' : 'var(--bg-secondary)',
              color: activeFilter === t ? '#fff' : 'var(--text-secondary)',
              border: `1px solid ${activeFilter === t ? 'var(--accent-blue)' : 'var(--border)'}`,
              transition: 'all .15s',
            }}
          >
            {t}
          </button>
        ))}
        {activeFilter !== 'ALL' && (
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            {filtered.length} of {logs.length} events
          </span>
        )}
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div style={{ padding: '48px 0', textAlign: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
          No events match the selected filter.
        </div>
      ) : (
        <div style={{ borderRadius: 12, border: '1px solid var(--border)', overflow: 'hidden', background: 'var(--bg-card)' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)' }}>
                  {['Timestamp', 'Record ID', 'Actor', 'Event Type', 'Payload'].map(h => (
                    <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: 11, letterSpacing: '.4px', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((log, i) => (
                  <tr key={log.id ?? i} style={{ borderBottom: '1px solid var(--border)', transition: 'background .1s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '10px 16px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', fontSize: 12 }}>
                      {formatTs(log.timestamp)}
                    </td>
                    <td style={{ padding: '10px 16px', fontFamily: 'monospace', fontSize: 12, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                      {log.record_id ?? '—'}
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <ActorBadge actor={log.actor} />
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <EventPill type={log.event_type} />
                    </td>
                    <td style={{ padding: '10px 16px', maxWidth: 280 }}>
                      <PayloadPreview payloadJson={log.payload_json} eventType={log.event_type} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
