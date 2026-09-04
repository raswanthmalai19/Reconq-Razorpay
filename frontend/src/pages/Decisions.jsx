import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Download, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { exportCsv } from '../api/client';

const STATUS_STYLES = {
  AUTO_MATCHED:       { bg: 'rgba(16,185,129,0.15)',  text: '#10b981', dot: '#10b981' },
  HUMAN_REVIEW:       { bg: 'rgba(245,158,11,0.15)',  text: '#f59e0b', dot: '#f59e0b' },
  UNRESOLVED:         { bg: 'rgba(239,68,68,0.15)',   text: '#ef4444', dot: '#ef4444' },
  BANK_CONFIRMED:     { bg: 'rgba(139,92,246,0.15)',  text: '#8b5cf6', dot: '#8b5cf6' },
  BANK_DISCREPANCY:   { bg: 'rgba(245,158,11,0.15)',  text: '#f59e0b', dot: '#f59e0b' },
  FUNDS_IN_TRANSIT:   { bg: 'rgba(59,130,246,0.15)',  text: '#3b82f6', dot: '#3b82f6' },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || { bg: 'rgba(148,163,184,0.15)', text: '#94a3b8', dot: '#94a3b8' };
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ background: s.bg, color: s.text }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.dot }} />
      {status.replace(/_/g, ' ')}
    </span>
  );
}

// Risk bands matching engine/risk_policy.py exactly
function getRiskBand(amountPaise) {
  const rupees = (amountPaise || 0) / 100;
  if (rupees < 1000)   return { label: '≤₹1K',     threshold: 0.75, color: '#10b981' };
  if (rupees < 25000)  return { label: '₹1K–25K',  threshold: 0.85, color: '#3b82f6' };
  if (rupees < 100000) return { label: '₹25K–1L',  threshold: 0.93, color: '#f59e0b' };
  return                       { label: '>₹1L',     threshold: 0.97, color: '#ef4444' };
}

function RiskBandBadge({ amountPaise }) {
  const band = getRiskBand(amountPaise);
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs font-mono font-semibold px-1.5 py-0.5 rounded" style={{
        background: `${band.color}15`, color: band.color, border: `1px solid ${band.color}30`,
      }}>
        {band.label}
      </span>
      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
        ≥{Math.round(band.threshold * 100)}%
      </span>
    </div>
  );
}

function ConfidenceBar({ value, amountPaise }) {
  if (value == null) return <span style={{ color: 'var(--text-secondary)' }}>—</span>;
  const pct = Math.round(value * 100);
  const band = getRiskBand(amountPaise);
  const requiredPct = Math.round(band.threshold * 100);
  // Color relative to the required threshold for this risk band
  const color = pct >= requiredPct ? '#10b981' : pct >= requiredPct - 5 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full relative" style={{ background: 'var(--bg-primary)', minWidth: 60 }}>
        {/* Threshold marker */}
        <div className="absolute top-0 h-1.5 w-px" style={{ left: `${requiredPct}%`, background: 'var(--text-secondary)', opacity: 0.5 }} />
        <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono font-semibold" style={{ color, minWidth: 34 }}>{pct}%</span>
    </div>
  );
}

const PAGE_SIZE = 20;

export default function Decisions({ results, runId }) {
  const navigate = useNavigate();
  const [query, setQuery]   = useState('');
  const [status, setStatus] = useState('ALL');
  const [page, setPage]     = useState(1);

  const matches = results?.matches || [];

  const filtered = useMemo(() => {
    return matches.filter(m => {
      const q = query.toLowerCase();
      const matchesQ = !q || m.settlement_id?.toLowerCase().includes(q) || m.invoice_id?.toLowerCase().includes(q);
      const matchesS = status === 'ALL' || m.status === status;
      return matchesQ && matchesS;
    });
  }, [matches, query, status]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const page_data  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const fmtAmt = v => v ? `₹${(v / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—';

  const handleExport = async () => {
    if (!runId) return;
    try {
      const blob = await exportCsv(runId);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url; a.download = `reconq_${runId.slice(0,8)}.csv`; a.click();
      URL.revokeObjectURL(url);
    } catch { alert('Export failed'); }
  };

  if (!results) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>No results yet.</p>
      <button onClick={() => navigate('/')} className="px-4 py-2 rounded-lg text-sm font-medium" style={{ background: 'var(--accent-blue)', color: '#fff' }}>
        ← Go to Dashboard
      </button>
    </div>
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Reconciliation Decisions</h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>
            {filtered.length} records · {matches.filter(m => m.status === 'AUTO_MATCHED').length} auto-matched
          </p>
        </div>
        <button
          onClick={handleExport}
          disabled={!runId}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all hover:opacity-80 disabled:opacity-40"
          style={{ border: '1px solid var(--border)', color: 'var(--text-primary)' }}
        >
          <Download size={15} /> Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-secondary)' }} />
          <input
            type="text"
            placeholder="Search by Settlement ID or Invoice…"
            value={query}
            onChange={e => { setQuery(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-4 py-2 rounded-lg text-sm outline-none"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          />
        </div>
        <div className="relative">
          <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-secondary)' }} />
          <select
            value={status}
            onChange={e => { setStatus(e.target.value); setPage(1); }}
            className="pl-9 pr-8 py-2 rounded-lg text-sm outline-none appearance-none"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          >
            {['ALL', 'AUTO_MATCHED', 'HUMAN_REVIEW', 'UNRESOLVED'].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--border)' }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: 'var(--bg-card)', borderBottom: '1px solid var(--border)' }}>
              {['Settlement ID', 'Invoice ID', 'Status', 'Risk Band', 'Confidence', 'Match Type', 'Amount'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {page_data.map((m, i) => (
              <tr
                key={`${m.settlement_id}-${i}`}
                className="border-t transition-colors hover:bg-white/[0.02]"
                style={{ borderColor: 'var(--border)' }}
              >
                <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--text-primary)' }}>{m.settlement_id || '—'}</td>
                <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{m.invoice_id || '—'}</td>
                <td className="px-4 py-3"><StatusBadge status={m.status} /></td>
                <td className="px-4 py-3"><RiskBandBadge amountPaise={m.amount_paise} /></td>
                <td className="px-4 py-3 min-w-32"><ConfidenceBar value={m.confidence} amountPaise={m.amount_paise} /></td>
                <td className="px-4 py-3 text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{m.match_type || '—'}</td>
                <td className="px-4 py-3 font-mono text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{fmtAmt(m.amount_paise)}</td>
              </tr>
            ))}
            {page_data.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
                  No records match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span style={{ color: 'var(--text-secondary)' }}>
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </span>
          <div className="flex gap-2">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="p-1.5 rounded-lg disabled:opacity-30 hover:bg-white/5" style={{ border: '1px solid var(--border)' }}>
              <ChevronLeft size={16} style={{ color: 'var(--text-primary)' }} />
            </button>
            <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)} className="p-1.5 rounded-lg disabled:opacity-30 hover:bg-white/5" style={{ border: '1px solid var(--border)' }}>
              <ChevronRight size={16} style={{ color: 'var(--text-primary)' }} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
