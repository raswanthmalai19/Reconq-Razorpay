import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Download, ChevronLeft, ChevronRight, Filter, Table2 } from 'lucide-react';
import { exportCsv } from '../api/client';
import Badge, { STATUS_STYLES } from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { Input, Select } from '../components/ui/Input';
import EmptyState from '../components/ui/EmptyState';

function getRiskBand(amountPaise) {
  const r = (amountPaise || 0) / 100;
  if (r < 1000)   return { label: '< ₹1K',    threshold: 75, color: '#16a34a' };
  if (r < 25000)  return { label: '₹1K–25K',  threshold: 85, color: '#2563eb' };
  if (r < 100000) return { label: '₹25K–1L',  threshold: 93, color: '#ca8a04' };
  return                  { label: '> ₹1L',    threshold: 97, color: '#dc2626' };
}

function ConfidenceBar({ value, amountPaise }) {
  if (value == null) return <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>;
  const pct = Math.round(value * 100);
  const band = getRiskBand(amountPaise);
  const color = pct >= band.threshold ? '#16a34a' : pct >= band.threshold - 5 ? '#ca8a04' : '#dc2626';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 120 }}>
      <div style={{ flex: 1, height: 4, borderRadius: 4, background: '#f0f0f0', position: 'relative', overflow: 'visible' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 4 }} />
        <div style={{ position: 'absolute', top: -2, left: `${band.threshold}%`, width: 1, height: 8, background: '#d4d4d8' }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 600, color, minWidth: 32 }}>{pct}%</span>
    </div>
  );
}

const PAGE_SIZE = 20;

export default function Decisions({ results, runId }) {
  const navigate = useNavigate();
  const [query, setQuery]   = useState('');
  const [status, setStatus] = useState('ALL');
  const [page, setPage]     = useState(1);
  const [exportError, setExportError] = useState('');

  const matches = results?.matches || [];

  const filtered = useMemo(() =>
    matches.filter(m => {
      const q = query.toLowerCase();
      const matchQ = !q || m.settlement_id?.toLowerCase().includes(q) || m.invoice_id?.toLowerCase().includes(q);
      const matchS = status === 'ALL' || m.status === status;
      return matchQ && matchS;
    }),
    [matches, query, status]
  );

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
  const pageData   = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const fmtAmt     = v => v ? `₹${(v / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—';

  const handleExport = async () => {
    if (!runId) return;
    setExportError('');
    try {
      const blob = await exportCsv(runId);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = `reconq_${runId.slice(0,8)}.csv`; a.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError('Export failed. Please try again.');
    }
  };

  if (!results) return (
    <EmptyState
      icon={Table2}
      title="No results yet"
      subtitle="Run a reconciliation from the Dashboard to see decisions here."
      actionLabel="Go to Dashboard"
      onAction={() => navigate('/')}
    />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: -0.3 }}>Reconciliation Decisions</h2>
          <p style={{ margin: '3px 0 0', fontSize: 13, color: 'var(--text-secondary)' }}>
            {filtered.length} records · {matches.filter(m => m.status === 'AUTO_MATCHED').length} auto-matched
          </p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <Button icon={Download} onClick={handleExport} disabled={!runId}>Export CSV</Button>
          {exportError && <span style={{ fontSize: 11, color: 'var(--accent-red)' }}>{exportError}</span>}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8 }}>
        <Input
          icon={Search}
          type="text" placeholder="Search settlement ID or invoice..."
          value={query} onChange={e => { setQuery(e.target.value); setPage(1); }}
          style={{ flex: 1, maxWidth: 340 }}
        />
        <div style={{ position: 'relative' }}>
          <Filter size={12} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
          <Select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }} style={{ paddingLeft: 28 }}>
            {['ALL', 'AUTO_MATCHED', 'HUMAN_REVIEW', 'UNRESOLVED'].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </Select>
        </div>
      </div>

      {/* Table */}
      <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border)' }}>
              {['Settlement ID', 'Invoice ID', 'Status', 'Risk Band', 'Confidence', 'Match Type', 'Amount'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '9px 12px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((m, i) => {
              const band = getRiskBand(m.amount_paise);
              return (
                <tr key={`${m.settlement_id}-${i}`} className="rq-row" style={{ borderTop: '1px solid var(--border-light)' }}>
                  <td style={{ padding: '9px 12px', fontFamily: 'monospace', fontSize: 11, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{m.settlement_id || '—'}</td>
                  <td style={{ padding: '9px 12px', fontFamily: 'monospace', fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{m.invoice_id || '—'}</td>
                  <td style={{ padding: '9px 12px' }}><Badge label={m.status} styleMap={STATUS_STYLES} dot /></td>
                  <td style={{ padding: '9px 12px', whiteSpace: 'nowrap' }}>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: band.color, fontWeight: 600 }}>{band.label}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 4 }}>≥{band.threshold}%</span>
                  </td>
                  <td style={{ padding: '9px 12px' }}><ConfidenceBar value={m.confidence} amountPaise={m.amount_paise} /></td>
                  <td style={{ padding: '9px 12px', fontSize: 12, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{m.match_type || '—'}</td>
                  <td style={{ padding: '9px 12px', fontFamily: 'monospace', fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{fmtAmt(m.amount_paise)}</td>
                </tr>
              );
            })}
            {pageData.length === 0 && (
              <tr><td colSpan={7} style={{ padding: '32px', textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>No records match your filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="rq-btn"
              style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid var(--border)', background: '#fff', cursor: page === 1 ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: page === 1 ? 0.4 : 1 }}>
              <ChevronLeft size={14} color="var(--text-primary)" />
            </button>
            <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)} className="rq-btn"
              style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid var(--border)', background: '#fff', cursor: page === totalPages ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: page === totalPages ? 0.4 : 1 }}>
              <ChevronRight size={14} color="var(--text-primary)" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
