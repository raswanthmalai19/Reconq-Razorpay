import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, Play, CheckCircle2, AlertCircle,
  TrendingUp, Banknote, ShieldAlert, Activity, Database
} from 'lucide-react';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import KPICard from '../components/KPICard';
import { reconcileFiles, reconcileSample, getComparison } from '../api/client';

const PIPELINE_STAGES = [
  'Loading CSVs',
  'Exact Match',
  'Blocking Buckets',
  'Group Detection',
  'ML Scoring',
  'Hungarian Assignment',
  'Risk Policy',
  'Bank Matching',
  'Anomaly Detection',
  'Complete ✓',
];

const STATUS_COLORS = {
  'Auto-Matched': '#10b981',
  'Human Review': '#f59e0b',
  'Unresolved':   '#ef4444',
};

const DONUT_COLORS = ['#10b981', '#f59e0b', '#ef4444'];

function UploadZone({ label, sublabel, type, file, onChange, optional }) {
  const ref = useRef();
  return (
    <div
      className="relative border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all hover:border-blue-500/50 hover:bg-blue-500/5"
      style={{ borderColor: file ? 'var(--accent-green)' : 'var(--border)', minHeight: 130 }}
      onClick={() => ref.current.click()}
    >
      <input ref={ref} type="file" accept=".csv" className="hidden" onChange={e => onChange(e.target.files[0])} />
      {file ? (
        <>
          <CheckCircle2 size={28} className="mb-2" style={{ color: 'var(--accent-green)' }} />
          <p className="text-sm font-semibold" style={{ color: 'var(--accent-green)' }}>{file.name}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Click to replace</p>
        </>
      ) : (
        <>
          <UploadCloud size={28} className="mb-2" style={{ color: 'var(--text-secondary)' }} />
          <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            {label} {optional && <span className="text-xs font-normal" style={{ color: 'var(--text-secondary)' }}>(Optional)</span>}
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{sublabel}</p>
        </>
      )}
    </div>
  );
}

function PipelineAnimation({ stage }) {
  const idx = PIPELINE_STAGES.indexOf(stage);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / PIPELINE_STAGES.length) * 100);
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium animate-pulse" style={{ color: 'var(--accent-blue)' }}>
          {stage || 'Initializing…'}
        </span>
        <span style={{ color: 'var(--text-secondary)' }}>{pct}%</span>
      </div>
      <div className="h-2 rounded-full" style={{ background: 'var(--bg-primary)' }}>
        <div
          className="h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)' }}
        />
      </div>
      <div className="flex gap-1 flex-wrap">
        {PIPELINE_STAGES.map((s, i) => (
          <span
            key={s}
            className="text-xs px-2 py-0.5 rounded-full transition-all"
            style={{
              background: i <= idx ? 'var(--accent-blue)' : 'var(--bg-primary)',
              color: i <= idx ? '#fff' : 'var(--text-secondary)',
              opacity: i <= idx ? 1 : 0.4,
            }}
          >
            {i < idx ? '✓' : ''} {s}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard({ results, setResults, runId, setRunId }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('');
  const [error, setError] = useState('');
  const [files, setFiles] = useState({ settlement: null, ledger: null, bank: null });
  const [showUpload, setShowUpload] = useState(true);

  const fmtRupees = (v) => {
    if (!v && v !== 0) return '—';
    if (v >= 10000000) return `₹${(v / 10000000).toFixed(1)}Cr`;
    if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
    if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
    return `₹${v.toFixed(0)}`;
  };

  const animate = (stages, cb) => {
    let i = 0;
    const t = setInterval(() => {
      setStage(stages[i]);
      i++;
      if (i >= stages.length) { clearInterval(t); cb(); }
    }, 350);
  };

  const handleRun = async (useSample = false) => {
    if (!useSample && (!files.settlement || !files.ledger)) {
      setError('Please upload at least Settlement CSV and Ledger CSV.');
      return;
    }
    setLoading(true); setError('');
    const stages = PIPELINE_STAGES.slice(0, -1);

    try {
      let data;
      if (useSample) {
        animate(stages, async () => {});
        data = await reconcileSample();
      } else {
        animate(stages, async () => {});
        data = await reconcileFiles(files.settlement, files.ledger, files.bank);
      }
      setStage('Complete ✓');
      setTimeout(() => {
        setResults(data);
        if (data.run_id) setRunId(data.run_id);
        setLoading(false);
        setStage('');
        setShowUpload(false); // Collapse upload section — results dominate now
      }, 800);
    } catch (err) {
      console.error(err);
      setError('Reconciliation failed. Is the backend running? (uvicorn api.main:app --reload)');
      setLoading(false);
      setStage('');
    }
  };

  const [comparison, setComparison] = useState(null);
  const [compLoading, setCompLoading] = useState(false);

  // Auto-fetch comparison whenever a run completes
  useEffect(() => {
    if (!results) return;
    setCompLoading(true);
    getComparison()
      .then(d => setComparison(d))
      .catch(() => {})
      .finally(() => setCompLoading(false));
  }, [results]);

  const kpi = results?.kpi;
  const pieData = kpi ? [
    { name: 'Auto-Matched', value: kpi.auto_matched || 0 },
    { name: 'Human Review', value: kpi.human_review || 0 },
    { name: 'Unresolved',   value: kpi.unresolved   || 0 },
  ] : [];

  // Build amount-band bar from matches
  const bandData = results?.matches ? (() => {
    const bands = { '₹0–1K': 0, '₹1K–25K': 0, '₹25K–1L': 0, '₹1L+': 0 };
    results.matches.forEach(m => {
      const r = (m.amount_paise || 0) / 100;
      if (r < 1000) bands['₹0–1K']++;
      else if (r < 25000) bands['₹1K–25K']++;
      else if (r < 100000) bands['₹25K–1L']++;
      else bands['₹1L+']++;
    });
    return Object.entries(bands).map(([name, count]) => ({ name, count }));
  })() : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            ReconQ — AI Finance Controller
          </h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
            3-way risk-weighted reconciliation · Gateway × Bank × Ledger · Powered by Gemini
          </p>
        </div>
        {results && (
          <span className="flex items-center gap-1.5 text-xs px-3 py-1 rounded-full" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>
            <Activity size={12} /> Live Results
          </span>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════
          COMPARISON BANNER — THE OPENING ACT
          "The naive 85% policy would have auto-cleared ₹X wrongly."
          This is the measurable claim. It runs on the same dataset,
          same ML model, only the decision policy differs.
      ═══════════════════════════════════════════════════════════════ */}
      {(comparison || compLoading) && (
        <div className="rounded-xl border-2 overflow-hidden" style={{ borderColor: '#3b82f6', background: 'rgba(59,130,246,0.04)' }}>
          <div className="px-5 py-3 flex items-center justify-between" style={{ background: 'rgba(59,130,246,0.1)' }}>
            <div className="flex items-center gap-2">
              <TrendingUp size={16} style={{ color: '#3b82f6' }} />
              <span className="text-sm font-bold" style={{ color: '#3b82f6' }}>
                Naive Baseline vs. Risk-Weighted Policy — Live Comparison
              </span>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full font-semibold" style={{ background: 'rgba(59,130,246,0.2)', color: '#3b82f6' }}>
              Same ML model · Same data · Different decision policy
            </span>
          </div>

          {compLoading ? (
            <div className="px-5 py-8 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
              Running comparison…
            </div>
          ) : comparison && (
            <div className="p-5 space-y-4">
              {/* Headline number */}
              <div className="rounded-lg p-4 text-center" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
                <p className="text-3xl font-black font-mono" style={{ color: '#ef4444' }}>
                  ₹{comparison.headline.rupees_naive_would_clear_wrong.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </p>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                  the naive 85% policy would have auto-cleared wrongly across{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{comparison.headline.transactions_caught} high-value transactions</strong>
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)', opacity: 0.7 }}>
                  risk-weighted policy correctly routed all of them to human review
                </p>
              </div>

              {/* Side-by-side policy boxes */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg p-3 border" style={{ borderColor: '#ef4444', background: 'rgba(239,68,68,0.05)' }}>
                  <p className="text-xs font-bold mb-2" style={{ color: '#ef4444' }}>
                    NAIVE — Flat {Math.round(comparison.naive_policy.threshold * 100)}% Threshold
                  </p>
                  <p className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{comparison.naive_policy.description}</p>
                  <div className="mt-2 space-y-1">
                    <div className="flex justify-between text-xs"><span style={{ color: 'var(--text-secondary)' }}>Auto-cleared</span><span className="font-bold" style={{ color: '#ef4444' }}>{comparison.naive_policy.auto_matched}</span></div>
                    <div className="flex justify-between text-xs"><span style={{ color: 'var(--text-secondary)' }}>In review</span><span className="font-mono">{comparison.naive_policy.human_review}</span></div>
                    <div className="flex justify-between text-xs font-bold border-t pt-1 mt-1" style={{ borderColor: 'var(--border)' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Total auto-cleared</span>
                      <span style={{ color: '#ef4444' }}>₹{(comparison.naive_policy.total_auto_cleared_rupees / 100000).toFixed(2)}L</span>
                    </div>
                  </div>
                </div>

                <div className="rounded-lg p-3 border" style={{ borderColor: '#10b981', background: 'rgba(16,185,129,0.05)' }}>
                  <p className="text-xs font-bold mb-2" style={{ color: '#10b981' }}>
                    RISK-WEIGHTED — Amount-Banded
                  </p>
                  <p className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{comparison.risk_weighted_policy.description}</p>
                  <div className="mt-2 space-y-1">
                    <div className="flex justify-between text-xs"><span style={{ color: 'var(--text-secondary)' }}>Auto-cleared</span><span className="font-bold" style={{ color: '#10b981' }}>{comparison.risk_weighted_policy.auto_matched}</span></div>
                    <div className="flex justify-between text-xs"><span style={{ color: 'var(--text-secondary)' }}>Sent to review</span><span className="font-mono">{comparison.risk_weighted_policy.human_review}</span></div>
                    <div className="flex justify-between text-xs font-bold border-t pt-1 mt-1" style={{ borderColor: 'var(--border)' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Total auto-cleared</span>
                      <span style={{ color: '#10b981' }}>₹{(comparison.risk_weighted_policy.total_auto_cleared_rupees / 100000).toFixed(2)}L</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Caught transactions table */}
              {comparison.caught_transactions?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                    Transactions naive cleared wrong (top {Math.min(5, comparison.caught_transactions.length)}):
                  </p>
                  <div className="rounded-lg overflow-hidden border" style={{ borderColor: 'var(--border)' }}>
                    <table className="w-full text-left text-xs">
                      <thead style={{ background: 'var(--bg-secondary)' }}>
                        <tr>
                          <th className="px-3 py-2" style={{ color: 'var(--text-secondary)' }}>Settlement ID</th>
                          <th className="px-3 py-2" style={{ color: 'var(--text-secondary)' }}>Amount</th>
                          <th className="px-3 py-2" style={{ color: 'var(--text-secondary)' }}>ML Confidence</th>
                          <th className="px-3 py-2" style={{ color: '#ef4444' }}>Naive said</th>
                          <th className="px-3 py-2" style={{ color: '#10b981' }}>We said</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparison.caught_transactions.slice(0, 5).map((t, i) => (
                          <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                            <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-primary)' }}>{t.settlement_id}</td>
                            <td className="px-3 py-2 font-mono font-bold" style={{ color: 'var(--text-primary)' }}>₹{t.amount_rupees.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                            <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{(t.confidence * 100).toFixed(1)}%</td>
                            <td className="px-3 py-2 font-bold" style={{ color: '#ef4444' }}>AUTO_MATCHED ✗</td>
                            <td className="px-3 py-2 font-bold" style={{ color: '#10b981' }}>HUMAN_REVIEW ✓</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Upload / Run Section — collapses after successful run */}
      {showUpload ? (
        <div className="rounded-xl border p-6 space-y-5" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Database size={16} style={{ color: 'var(--accent-blue)' }} />
            <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Upload CSV Files</span>
            <span className="text-xs ml-auto" style={{ color: 'var(--text-secondary)' }}>Or use the built-in sample dataset →</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <UploadZone label="Settlement Report" sublabel="Gateway settlement CSV" type="settlement" file={files.settlement} onChange={f => setFiles(p => ({ ...p, settlement: f }))} />
            <UploadZone label="Internal Ledger"   sublabel="Accounting ledger CSV" type="ledger"     file={files.ledger}     onChange={f => setFiles(p => ({ ...p, ledger: f }))} />
            <UploadZone label="Bank Statement"     sublabel="Bank account statement" type="bank"       file={files.bank}       onChange={f => setFiles(p => ({ ...p, bank: f }))} optional />
          </div>

          {loading && <PipelineAnimation stage={stage} />}
          {error && <p className="text-sm px-3 py-2 rounded-lg" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}>{error}</p>}

          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={() => handleRun(false)}
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg font-semibold text-sm transition-all disabled:opacity-50 hover:opacity-90 active:scale-95"
              style={{ background: 'linear-gradient(135deg, #3b82f6, #6366f1)', color: '#fff' }}
            >
              <Play size={16} fill="white" /> Run Reconciliation
            </button>
            <button
              onClick={() => handleRun(true)}
              disabled={loading}
              className="px-5 py-2.5 rounded-lg font-medium text-sm transition-all hover:bg-white/10 active:scale-95"
              style={{ border: '1px solid var(--border)', color: 'var(--text-primary)' }}
            >
              ⚡ Use Sample Data
            </button>
          </div>
        </div>
      ) : (
        /* Collapsed state — compact re-run bar + navigation */
        <div className="rounded-xl border p-4" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} style={{ color: 'var(--accent-green)' }} />
              <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Reconciliation complete — Run <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{runId?.slice(0, 8)}…</span>
              </span>
            </div>
            <button
              onClick={() => setShowUpload(true)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-white/10"
              style={{ border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              ↻ Re-run with different data
            </button>
            <div className="flex items-center gap-2 ml-auto">
              <button
                onClick={() => navigate('/decisions')}
                className="flex items-center gap-2 px-5 py-2 rounded-lg font-semibold text-sm transition-all hover:opacity-90 active:scale-95"
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff' }}
              >
                View All Decisions →
              </button>
              <button
                onClick={() => navigate('/exceptions')}
                className="px-4 py-2 rounded-lg font-medium text-sm"
                style={{ border: '1px solid rgba(245,158,11,0.4)', color: '#f59e0b' }}
              >
                Exceptions ({kpi?.human_review || 0})
              </button>
              <button
                onClick={() => navigate('/anomalies')}
                className="px-4 py-2 rounded-lg font-medium text-sm"
                style={{ border: '1px solid rgba(239,68,68,0.4)', color: '#ef4444' }}
              >
                Anomalies ({results?.anomalies?.length || 0})
              </button>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      {results && kpi && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
            <KPICard title="Match Rate"      value={`${(kpi.match_rate * 100).toFixed(1)}%`}   subtitle={`${kpi.auto_matched} auto-cleared`}     icon={TrendingUp}   color="blue" />
            <KPICard title="Auto-Cleared"    value={fmtRupees(kpi.rupees_auto_cleared)}         subtitle="Processed instantly"                      icon={CheckCircle2} color="green" />
            <KPICard title="In Review"       value={fmtRupees(kpi.rupees_in_review)}            subtitle={`${kpi.human_review} items`}              icon={AlertCircle}  color="yellow" />
            <KPICard title="Unresolved"      value={kpi.unresolved}                             subtitle="Need investigation"                        icon={ShieldAlert}  color="red" />
            <KPICard title="Bank Confirmed"  value={kpi.bank_confirmed || 0}                    subtitle="3-way match"                              icon={Banknote}     color="purple" />
            <KPICard title="Leakage Flagged" value={fmtRupees(results.leakage_report?.total_leakage_rupees || 0)} subtitle={`${results.anomalies?.length || 0} anomalies`} icon={ShieldAlert} color="red" />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Donut */}
            <div className="rounded-xl border p-6" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>STATUS DISTRIBUTION</h3>
              <div className="h-56 flex items-center">
                <ResponsiveContainer width="55%" height="100%">
                  <PieChart>
                    <Pie data={pieData} innerRadius={55} outerRadius={75} paddingAngle={4} dataKey="value" strokeWidth={0}>
                      {pieData.map((_, i) => <Cell key={i} fill={DONUT_COLORS[i]} />)}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                      formatter={(v, n) => [`${v} records`, n]}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-3 ml-4">
                  {pieData.map((d, i) => (
                    <div key={d.name} className="flex items-center gap-2 text-sm">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ background: DONUT_COLORS[i] }} />
                      <span style={{ color: 'var(--text-secondary)' }}>{d.name}</span>
                      <span className="ml-auto font-semibold" style={{ color: 'var(--text-primary)' }}>{d.value}</span>
                    </div>
                  ))}
                  <div className="pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
                    <div className="flex justify-between text-xs">
                      <span style={{ color: 'var(--text-secondary)' }}>Total</span>
                      <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{kpi.total_records}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Bar chart */}
            <div className="rounded-xl border p-6" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>VOLUME BY AMOUNT BAND</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={bandData} barCategoryGap="30%">
                    <XAxis dataKey="name" stroke="var(--text-secondary)" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--text-secondary)" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                      cursor={{ fill: 'rgba(59,130,246,0.05)' }}
                      formatter={v => [`${v} settlements`]}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {bandData.map((_, i) => (
                        <Cell key={i} fill={i === 3 ? '#ef4444' : '#3b82f6'} opacity={0.8 + i * 0.05} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Bank 3-way summary strip */}
          {kpi.bank_confirmed > 0 && (
            <div className="rounded-xl border p-5" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-2 mb-4">
                <Banknote size={16} style={{ color: 'var(--accent-purple)' }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>3-Way Bank Reconciliation</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'Bank Confirmed',    value: kpi.bank_confirmed,   color: '#10b981' },
                  { label: 'Bank Discrepancies',value: results.matches?.filter(m => m.status === 'BANK_DISCREPANCY').length || 0, color: '#f59e0b' },
                  { label: 'Funds in Transit',  value: kpi.funds_in_transit, color: '#8b5cf6' },
                  { label: 'Anomalies Detected',value: results.anomalies?.length || 0, color: '#ef4444' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="text-center">
                    <div className="text-2xl font-bold" style={{ color }}>{value}</div>
                    <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Engineering credibility footer */}
          <div className="rounded-xl border p-4" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border)' }}>
            <div className="flex items-center justify-center gap-6 flex-wrap">
              {[
                { label: '39 automated tests', color: '#10b981' },
                { label: 'Risk-weighted decisioning', color: '#3b82f6' },
                { label: 'Immutable audit log', color: '#8b5cf6' },
                { label: 'Numeric cross-check on AI', color: '#f59e0b' },
                { label: 'Gemini function-calling', color: '#ec4899' },
              ].map(({ label, color }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                  <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Empty state */}
      {!results && !loading && (
        <div className="rounded-xl border border-dashed p-12 text-center" style={{ borderColor: 'var(--border)' }}>
          <Activity size={40} className="mx-auto mb-4 opacity-30" style={{ color: 'var(--text-secondary)' }} />
          <p className="text-lg font-semibold" style={{ color: 'var(--text-secondary)' }}>No reconciliation run yet</p>
          <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)', opacity: 0.6 }}>
            Upload your files above or click <strong>⚡ Use Sample Data</strong> to see the dashboard in action.
          </p>
        </div>
      )}
    </div>
  );
}
