import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Check, X, Info, AlertTriangle, CheckCircle, XCircle,
  Wrench, ShieldCheck, ShieldAlert
} from 'lucide-react';
import { submitOverride, getSuggestedFix, approveSuggestedFix } from '../api/client';
import Badge, { STATUS_STYLES } from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { TextArea } from '../components/ui/Input';
import EmptyState from '../components/ui/EmptyState';
import { SkeletonRows } from '../components/ui/Skeleton';

function formatAmount(paise) {
  if (paise == null) return '—';
  const rupees = paise / 100;
  if (rupees >= 1_00_00_000) return `₹${(rupees / 1_00_00_000).toFixed(2)}Cr`;
  if (rupees >= 1_00_000)    return `₹${(rupees / 1_00_000).toFixed(2)}L`;
  if (rupees >= 1_000)       return `₹${(rupees / 1_000).toFixed(2)}K`;
  return `₹${rupees.toFixed(2)}`;
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 70 ? 'var(--accent-blue)' : pct >= 50 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 5, borderRadius: 99, background: 'var(--bg-secondary)', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 99, transition: 'width .3s' }} />
      </div>
      <span style={{ fontSize: 11, color: 'var(--text-secondary)', minWidth: 30, textAlign: 'right' }}>{pct}%</span>
    </div>
  );
}

function FieldGrid({ title, data }) {
  return (
    <div style={{ padding: 16, borderRadius: 10, background: 'var(--bg-secondary)', border: '1px solid var(--border)', flex: 1 }}>
      <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '.5px' }}>{title}</p>
      {!data || typeof data !== 'object' ? (
        <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>No data available</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {Object.entries(data).map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 110 }}>{k.replace(/_/g, ' ')}</span>
              <span style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)', textAlign: 'right', wordBreak: 'break-all' }}>{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   SUGGESTED FIX PANEL
   - Shows the LLM-generated proposal inline (not in a modal)
   - Displays validation status (cross-check passed/failed)
   - "Approve" writes to audit log ONLY
   - UI text explicitly states: "Nothing is sent externally"
═══════════════════════════════════════════════════════════════════════ */
function SuggestedFixPanel({ fix, onApprove, approveLoading, approved }) {
  if (!fix) return null;

  const isNoFix = fix.adjustment_type === 'no_confident_fix';
  const crossCheckPassed = fix.validation?.cross_check_passed;
  const tone = isNoFix ? '#f59e0b' : crossCheckPassed ? '#10b981' : '#ef4444';

  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', marginBottom: 14, border: `1px solid ${tone}4d` }}>
      {/* Header */}
      <div style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8, background: `${tone}14` }}>
        <Wrench size={14} style={{ color: tone }} />
        <span style={{ fontSize: 12, fontWeight: 700, color: tone }}>
          Suggested Fix — {fix.adjustment_type?.replace(/_/g, ' ').toUpperCase()}
        </span>

        <span style={{
          marginLeft: 'auto', fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 99,
          display: 'flex', alignItems: 'center', gap: 4,
          background: crossCheckPassed ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
          color: crossCheckPassed ? '#10b981' : '#ef4444',
        }}>
          {crossCheckPassed ? <ShieldCheck size={10} /> : <ShieldAlert size={10} />}
          {crossCheckPassed ? 'CROSS-CHECK PASSED' : 'CROSS-CHECK FAILED'}
        </span>
      </div>

      {/* Body */}
      <div style={{ padding: 16 }}>
        <p style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.6, marginBottom: 12 }}>
          {fix.explanation}
        </p>

        {fix.affected_records?.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>PROPOSED ADJUSTMENTS</p>
            <div style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
              <table style={{ width: '100%', fontSize: 11, textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead style={{ background: 'var(--bg-secondary)' }}>
                  <tr>
                    <th style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>Record</th>
                    <th style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>Field</th>
                    <th style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>Current</th>
                    <th style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>Proposed</th>
                    <th style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {fix.affected_records.map((r, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                      <td style={{ padding: '6px 10px', fontFamily: 'monospace', color: 'var(--text-primary)' }}>{r.record_id}</td>
                      <td style={{ padding: '6px 10px', color: 'var(--text-secondary)' }}>{r.field}</td>
                      <td style={{ padding: '6px 10px', fontFamily: 'monospace', color: '#ef4444' }}>{r.current_value}</td>
                      <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontWeight: 700, color: '#10b981' }}>{r.proposed_value}</td>
                      <td style={{ padding: '6px 10px', color: 'var(--text-secondary)', fontSize: 10 }}>{r.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {fix.confidence != null && !isNoFix && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Fix confidence:</span>
            <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'monospace', color: fix.confidence >= 0.8 ? '#10b981' : fix.confidence >= 0.5 ? '#f59e0b' : '#ef4444' }}>
              {(fix.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {fix.human_next_step && (
          <div style={{
            padding: '10px 14px', borderRadius: 8, fontSize: 11, lineHeight: 1.5,
            background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.15)',
            color: 'var(--text-secondary)',
          }}>
            <strong style={{ color: 'var(--accent-blue)' }}>Your next step:</strong> {fix.human_next_step}
          </div>
        )}

        {!isNoFix && crossCheckPassed && (
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {approved ? (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderRadius: 8,
                background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)',
              }}>
                <CheckCircle size={14} style={{ color: '#10b981' }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: '#10b981' }}>
                  Approved — logged to audit trail
                </span>
              </div>
            ) : (
              <Button variant="success" size="lg" icon={Check} loading={approveLoading} onClick={onApprove}>
                {approveLoading ? 'Logging…' : 'Approve Fix'}
              </Button>
            )}
            <p style={{ fontSize: 9, color: 'var(--text-secondary)', opacity: 0.6, textAlign: 'center' }}>
              Approving logs this internally — nothing is sent externally. To apply this fix, your finance team reviews the audit log and executes through your own ledger system.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}


export default function Exceptions({ results, runId }) {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState('');
  const [overrides, setOverrides] = useState({});
  const [loading, setLoading] = useState(false);

  // Suggested fix state
  const [fixLoading, setFixLoading] = useState(false);
  const [fixes, setFixes] = useState({});         // keyed by settlement_id
  const [approveLoading, setApproveLoading] = useState(false);
  const [approved, setApproved] = useState({});    // keyed by settlement_id

  const handleGetFix = async () => {
    if (!selected) return;
    const sid = selected.settlement_id;
    setFixLoading(true);
    try {
      const data = await getSuggestedFix({
        settlement_id: sid,
        invoice_id: selected.invoice_id,
        amount_paise: selected.amount_paise,
        confidence: selected.confidence,
        status: selected.status,
        match_type: selected.match_type,
      });
      setFixes(prev => ({ ...prev, [sid]: data }));
    } catch (err) {
      console.error('getSuggestedFix error:', err);
      setFixes(prev => ({
        ...prev,
        [sid]: {
          adjustment_type: 'no_confident_fix',
          affected_records: [],
          confidence: 0,
          explanation: 'Failed to reach the AI service. Please try again.',
          human_next_step: 'Check that the backend is running and retry.',
          validation: { cross_check_passed: false },
        },
      }));
    } finally {
      setFixLoading(false);
    }
  };

  const handleApproveFix = async () => {
    if (!selected) return;
    const sid = selected.settlement_id;
    const fix = fixes[sid];
    if (!fix) return;
    setApproveLoading(true);
    try {
      await approveSuggestedFix(sid, runId || 'manual', fix);
      setApproved(prev => ({ ...prev, [sid]: true }));
    } catch (err) {
      console.error('approveSuggestedFix error:', err);
    } finally {
      setApproveLoading(false);
    }
  };

  const exceptions = (results?.matches ?? []).filter(
    m => m.status === 'HUMAN_REVIEW' || m.status === 'UNRESOLVED'
  );

  if (!results) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Run reconciliation first"
        actionLabel="Go to Dashboard"
        onAction={() => navigate('/')}
      />
    );
  }

  if (exceptions.length === 0) {
    return (
      <EmptyState
        icon={CheckCircle}
        tone="success"
        title="All transactions auto-matched!"
        subtitle="No human review required for this run."
      />
    );
  }

  const handleAction = async (decision) => {
    if (!selected) return;
    setLoading(true);
    try {
      await submitOverride(selected.settlement_id, decision, notes.trim());
      setOverrides(prev => ({ ...prev, [selected.settlement_id]: { decision, success: true } }));
    } catch (err) {
      console.error('submitOverride error:', err);
      setOverrides(prev => ({ ...prev, [selected.settlement_id]: { decision, success: false } }));
    } finally {
      setLoading(false);
      setNotes('');
    }
  };

  const override = selected ? overrides[selected.settlement_id] : null;
  const currentFix = selected ? fixes[selected.settlement_id] : null;
  const currentApproved = selected ? approved[selected.settlement_id] : false;

  return (
    <div style={{ display: 'flex', height: '100%', gap: 20 }}>
      {/* LEFT PANEL — exception queue */}
      <div style={{ width: 320, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 0 }}>
        <div style={{ marginBottom: 14 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)' }}>Exceptions Queue</h2>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{exceptions.length} item{exceptions.length !== 1 ? 's' : ''} need review</p>
        </div>
        <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
          {exceptions.map(exc => {
            const ov = overrides[exc.settlement_id];
            const hasFix = !!fixes[exc.settlement_id];
            const isActive = selected?.settlement_id === exc.settlement_id;
            return (
              <div
                key={exc.settlement_id}
                onClick={() => { setSelected(exc); setNotes(''); }}
                style={{
                  padding: 14, borderRadius: 10,
                  border: `1px solid ${isActive ? 'var(--accent-blue)' : 'var(--border)'}`,
                  background: isActive ? 'rgba(59,130,246,0.08)' : 'var(--bg-card)',
                  cursor: 'pointer', transition: 'all .15s', position: 'relative',
                }}
              >
                {ov && (
                  <div style={{
                    position: 'absolute', top: 8, right: 8, fontSize: 9, fontWeight: 700,
                    letterSpacing: '.5px', padding: '1px 6px', borderRadius: 99,
                    background: ov.decision === 'ACCEPT' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                    color: ov.decision === 'ACCEPT' ? '#10b981' : '#ef4444',
                  }}>
                    {ov.decision === 'ACCEPT' ? '✓ ACCEPTED' : '✗ UNRESOLVED'}
                  </div>
                )}
                {!ov && hasFix && (
                  <div style={{
                    position: 'absolute', top: 8, right: 8, fontSize: 9, fontWeight: 700,
                    padding: '1px 6px', borderRadius: 99,
                    background: 'rgba(139,92,246,0.15)', color: '#8b5cf6',
                  }}>
                    FIX READY
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{exc.settlement_id}</span>
                  <Badge label={exc.status} styleMap={STATUS_STYLES} size="sm" />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8 }}>
                  {exc.invoice_id} · {exc.match_type} · {formatAmount(exc.amount_paise)}
                </div>
                <ConfidenceBar value={exc.confidence} />
              </div>
            );
          })}
        </div>
      </div>

      {/* RIGHT PANEL — detail + suggested fix */}
      <Card style={{ flex: 1, borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
        {selected ? (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0 }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18, flexWrap: 'wrap', gap: 8 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <h2 style={{ fontSize: 20, fontWeight: 700, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{selected.settlement_id}</h2>
                  <Badge label={selected.status} styleMap={STATUS_STYLES} />
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>
                  Invoice: <span style={{ fontFamily: 'monospace' }}>{selected.invoice_id}</span>
                  &nbsp;·&nbsp;Match type: {selected.match_type}
                  &nbsp;·&nbsp;{formatAmount(selected.amount_paise)}
                </p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>
                  {Math.round((selected.confidence ?? 0) * 100)}%
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>confidence</div>
              </div>
            </div>

            {/* Explanation box */}
            <div style={{ display: 'flex', gap: 12, padding: '12px 16px', borderRadius: 10, background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.25)', marginBottom: 18 }}>
              <Info size={16} style={{ color: 'var(--accent-blue)', flexShrink: 0, marginTop: 1 }} />
              <div>
                <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-blue)', marginBottom: 2 }}>Why this needs review</p>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  Confidence below auto-clear threshold for this amount band — requires human judgment.
                </p>
              </div>
            </div>

            {/* Two-column record view */}
            <div style={{ display: 'flex', gap: 14, marginBottom: 18, flexShrink: 0, flexWrap: 'wrap' }}>
              <FieldGrid
                title="Settlement Record"
                data={{
                  settlement_id: selected.settlement_id,
                  amount_paise: selected.amount_paise,
                  amount_formatted: formatAmount(selected.amount_paise),
                  match_type: selected.match_type,
                  confidence: `${Math.round((selected.confidence ?? 0) * 100)}%`,
                  status: selected.status,
                }}
              />
              <FieldGrid
                title="Ledger Record"
                data={{
                  invoice_id: selected.invoice_id,
                  match_type: selected.match_type,
                  confidence: `${Math.round((selected.confidence ?? 0) * 100)}%`,
                  status: selected.status,
                  amount_paise: selected.amount_paise,
                  amount_formatted: formatAmount(selected.amount_paise),
                }}
              />
            </div>

            {/* SUGGESTED FIX — inline panel, not a modal */}
            {currentFix ? (
              <SuggestedFixPanel
                fix={currentFix}
                onApprove={handleApproveFix}
                approveLoading={approveLoading}
                approved={currentApproved}
              />
            ) : fixLoading ? (
              <div style={{ marginBottom: 14 }}><SkeletonRows rows={2} cols={4} /></div>
            ) : (
              <Button variant="purple" size="lg" icon={Wrench} onClick={handleGetFix} style={{ marginBottom: 14, alignSelf: 'flex-start' }}>
                Get Suggested Fix
              </Button>
            )}

            {/* Notes */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>REVIEWER NOTES</label>
              <TextArea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Add notes about your decision (optional)…"
                rows={3}
              />
            </div>

            {/* Confirmation banner */}
            {override && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', borderRadius: 8, marginBottom: 14,
                background: override.decision === 'ACCEPT' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                border: `1px solid ${override.decision === 'ACCEPT' ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)'}`,
              }}>
                {override.decision === 'ACCEPT'
                  ? <CheckCircle size={16} style={{ color: '#10b981' }} />
                  : <XCircle size={16} style={{ color: '#ef4444' }} />}
                <span style={{ fontSize: 13, fontWeight: 600, color: override.decision === 'ACCEPT' ? '#10b981' : '#ef4444' }}>
                  {override.decision === 'ACCEPT'
                    ? `Match accepted for ${selected.settlement_id}`
                    : `Marked as unresolved for ${selected.settlement_id}`}
                </span>
              </div>
            )}

            {/* Accept / Reject buttons */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 'auto' }}>
              <Button variant="danger" size="lg" icon={X} disabled={loading || !!override} onClick={() => handleAction('REJECT')}>
                Mark Unresolved
              </Button>
              <Button variant="success" size="lg" icon={Check} loading={loading} disabled={!!override} onClick={() => handleAction('ACCEPT')}>
                {loading ? 'Submitting…' : 'Accept Match'}
              </Button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 10 }}>
            <AlertTriangle size={32} style={{ color: 'var(--text-secondary)', opacity: 0.3 }} />
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Select an exception from the queue to review</p>
          </div>
        )}
      </Card>
    </div>
  );
}
