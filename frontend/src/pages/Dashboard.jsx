import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, Play, CheckCircle2, AlertCircle, Info,
  TrendingUp, Banknote, ShieldAlert, Activity, Database, RefreshCw, Zap
} from 'lucide-react';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer
} from 'recharts';
import KPICard from '../components/KPICard';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import { SkeletonKPIGrid, SkeletonBlock } from '../components/ui/Skeleton';
import { reconcileFiles, reconcileSample, getComparison, syncRazorpay, getRazorpayStatus } from '../api/client';

const PIPELINE_STAGES = [
  'Loading CSVs', 'Exact Match', 'Blocking Buckets', 'Group Detection',
  'ML Scoring', 'Hungarian Assignment', 'Risk Policy', 'Bank Matching', 'Anomaly Detection', 'Done',
];

const DONUT_COLORS = ['#2563eb', '#ca8a04', '#dc2626'];
const MAX_CSV_SIZE_MB = 10;

const fmtRupees = (v) => {
  if (!v && v !== 0) return '—';
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(2)}Cr`;
  if (v >= 100000)   return `₹${(v / 100000).toFixed(2)}L`;
  if (v >= 1000)     return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${Math.round(v)}`;
};

function UploadZone({ label, sublabel, file, onChange, optional, error }) {
  const ref = useRef();
  return (
    <div>
      <div
        onClick={() => ref.current.click()}
        className="rq-card-hover"
        style={{
          border: `1px dashed ${error ? 'var(--accent-red)' : file ? 'var(--accent-green)' : 'var(--border)'}`,
          borderRadius: 8, padding: '18px 14px',
          display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
          cursor: 'pointer', background: error ? 'var(--accent-red-light)' : file ? 'var(--accent-green-light)' : 'var(--bg-subtle)',
          minHeight: 100, justifyContent: 'center',
        }}
      >
        <input
          ref={ref} type="file" accept=".csv" style={{ display: 'none' }}
          onChange={e => onChange(e.target.files[0])}
        />
        {file ? (
          <>
            <CheckCircle2 size={20} color="var(--accent-green)" style={{ marginBottom: 6 }} />
            <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: 'var(--accent-green)' }}>{file.name}</p>
            <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--text-muted)' }}>Click to replace</p>
          </>
        ) : (
          <>
            <UploadCloud size={20} color="var(--text-muted)" style={{ marginBottom: 6 }} />
            <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
              {label} {optional && <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>}
            </p>
            <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--text-muted)' }}>{sublabel}</p>
          </>
        )}
      </div>
      {error && <p style={{ margin: '4px 0 0', fontSize: 11, color: 'var(--accent-red)' }}>{error}</p>}
    </div>
  );
}

function PipelineBar({ stage }) {
  const idx = PIPELINE_STAGES.indexOf(stage);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / PIPELINE_STAGES.length) * 100);
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: 'var(--accent-blue)', fontWeight: 500 }}>{stage || 'Starting...'}</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{pct}%</span>
      </div>
      <div style={{ height: 4, borderRadius: 4, background: '#e4e4e7', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: 'var(--accent-blue)', borderRadius: 4, transition: 'width 0.4s' }} />
      </div>
    </div>
  );
}

function validateCsv(file) {
  if (!file) return null;
  if (!file.name.toLowerCase().endsWith('.csv')) return 'Only .csv files are accepted.';
  if (file.size > MAX_CSV_SIZE_MB * 1024 * 1024) return `File exceeds ${MAX_CSV_SIZE_MB}MB limit.`;
  if (file.size === 0) return 'File is empty.';
  return null;
}

export default function Dashboard({ results, setResults, runId, setRunId }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('');
  const [error, setError] = useState('');
  const [files, setFiles] = useState({ settlement: null, ledger: null, bank: null });
  const [fileErrors, setFileErrors] = useState({});
  const [showUpload, setShowUpload] = useState(true);
  const [comparison, setComparison] = useState(null);
  const [compLoading, setCompLoading] = useState(false);

  // Data Source Tab State
  const [sourceTab, setSourceTab] = useState('csv'); // 'csv' or 'api'
  const [apiStatus, setApiStatus] = useState(null);
  const [noSettlements, setNoSettlements] = useState(null); // honest empty-state message from Razorpay sync

  useEffect(() => {
    if (!results) return;
    setCompLoading(true);
    getComparison()
      .then(d => setComparison(d))
      .catch(() => {})
      .finally(() => setCompLoading(false));
  }, [results]);

  useEffect(() => {
    if (sourceTab === 'api' && !apiStatus) {
      getRazorpayStatus().then(setApiStatus).catch(() => {});
    }
  }, [sourceTab, apiStatus]);

  const animate = (stages, cb) => {
    let i = 0;
    const t = setInterval(() => {
      setStage(stages[i]);
      i++;
      if (i >= stages.length) { clearInterval(t); cb(); }
    }, 380);
  };

  const setFile = (key, file) => {
    setFiles(p => ({ ...p, [key]: file }));
    setFileErrors(p => ({ ...p, [key]: validateCsv(file) }));
  };

  const handleRun = async (useSample = false) => {
    setError(''); setNoSettlements(null);

    if (sourceTab === 'csv' && !useSample) {
      const errs = {
        settlement: validateCsv(files.settlement) || (!files.settlement ? 'Required.' : null),
        ledger: validateCsv(files.ledger) || (!files.ledger ? 'Required.' : null),
        bank: validateCsv(files.bank),
      };
      setFileErrors(errs);
      if (errs.settlement || errs.ledger || errs.bank) {
        setError('Fix the highlighted files before running.');
        return;
      }
    }

    setLoading(true);
    const stages = PIPELINE_STAGES.slice(0, -1);
    try {
      let data;
      if (sourceTab === 'api') {
        animate(stages, () => {});
        data = await syncRazorpay();
        if (data.status === 'no_settlements') {
          setNoSettlements(data.razorpay_message);
          setLoading(false); setStage('');
          return;
        }
      } else {
        if (useSample) { animate(stages, () => {}); data = await reconcileSample(); }
        else { animate(stages, () => {}); data = await reconcileFiles(files.settlement, files.ledger, files.bank); }
      }
      setStage('Done');
      setTimeout(() => {
        setResults(data);
        if (data.run_id) setRunId(data.run_id);
        setLoading(false); setStage('');
        setShowUpload(false);
      }, 600);
    } catch (err) {
      setError(err.message || 'Reconciliation failed. Is the backend running?');
      setLoading(false); setStage('');
    }
  };

  const kpi = results?.kpi;

  const pieData = kpi ? [
    { name: 'Auto-Matched', value: kpi.auto_matched || 0 },
    { name: 'Human Review', value: kpi.human_review || 0 },
    { name: 'Unresolved',   value: kpi.unresolved   || 0 },
  ] : [];

  const bandData = results?.matches ? (() => {
    const b = { '< ₹1K': 0, '₹1K–25K': 0, '₹25K–1L': 0, '> ₹1L': 0 };
    results.matches.forEach(m => {
      const r = (m.amount_paise || 0) / 100;
      if (r < 1000)        b['< ₹1K']++;
      else if (r < 25000)  b['₹1K–25K']++;
      else if (r < 100000) b['₹25K–1L']++;
      else                 b['> ₹1L']++;
    });
    return Object.entries(b).map(([name, count]) => ({ name, count }));
  })() : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 21, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: -0.4 }}>
            Finance Controller
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-secondary)' }}>
            Built for Razorpay Merchants · Automated Settlement Reconciler for ERP Ledgers (Tally, SAP, Zoho)
          </p>
        </div>
        {results && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--accent-green)', background: 'var(--accent-green-light)', padding: '5px 10px', borderRadius: 6, border: '1px solid #bbf7d0' }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-green)' }} />
            Results ready
          </div>
        )}
      </div>

      {/* Ledger disclosure for Razorpay live path */}
      {results?.razorpay_source === 'razorpay_live' && results?.ledger_message && (
        <Card padding="12px 16px" style={{ background: 'var(--accent-blue-light)', border: '1px solid #bfdbfe' }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <Info size={15} color="var(--accent-blue)" style={{ flexShrink: 0, marginTop: 1 }} />
            <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <strong style={{ color: 'var(--accent-blue)' }}>Live Razorpay settlements, synthetic ledger:</strong> {results.ledger_message}
            </p>
          </div>
        </Card>
      )}

      {/* Comparison banner */}
      {(comparison || compLoading) && (
        <Card padding="18px 20px">
          <p style={{ margin: '0 0 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Naive Baseline vs Risk-Weighted — Same model, same data
          </p>

          {compLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <SkeletonBlock height={64} radius={8} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <SkeletonBlock height={90} radius={8} />
                <SkeletonBlock height={90} radius={8} />
              </div>
            </div>
          ) : comparison && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Hero number */}
              <div style={{ padding: '14px 16px', background: 'var(--accent-red-light)', borderRadius: 8, border: '1px solid #fecaca' }}>
                <p style={{ margin: 0, fontSize: 26, fontWeight: 700, color: 'var(--accent-red)', letterSpacing: -0.5 }}>
                  ₹{comparison.headline.rupees_naive_would_clear_wrong.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </p>
                <p style={{ margin: '5px 0 0', fontSize: 13, color: '#7f1d1d' }}>
                  the flat 85% threshold would have auto-cleared across{' '}
                  <strong>{comparison.headline.transactions_caught} transactions</strong>.
                  Risk-weighted policy caught all of them.
                </p>
              </div>

              {/* Policy comparison */}
              <div className="rq-chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Flat 85% Threshold (Naive)', data: comparison.naive_policy, borderColor: '#fca5a5', bg: '#fff7f7', valueColor: 'var(--accent-red)' },
                  { label: 'Risk-Weighted (ReconQ)', data: comparison.risk_weighted_policy, borderColor: '#86efac', bg: 'var(--accent-green-light)', valueColor: 'var(--accent-green)' },
                ].map(({ label, data, borderColor, bg, valueColor }) => (
                  <div key={label} style={{ padding: '12px 14px', background: bg, border: `1px solid ${borderColor}`, borderRadius: 8 }}>
                    <p style={{ margin: '0 0 10px', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>{label}</p>
                    {[
                      ['Auto-cleared', data.auto_matched],
                      ['In review', data.human_review],
                    ].map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                        <span style={{ fontWeight: 600, color: valueColor }}>{v}</span>
                      </div>
                    ))}
                    <div style={{ borderTop: '1px solid var(--border)', paddingTop: 6, marginTop: 4, display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Total auto-cleared</span>
                      <span style={{ fontWeight: 700, color: valueColor }}>
                        ₹{(data.total_auto_cleared_rupees / 100000).toFixed(2)}L
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Caught table */}
              {comparison.caught_transactions?.length > 0 && (
                <div>
                  <p style={{ margin: '0 0 8px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    Transactions caught by risk policy (top {Math.min(5, comparison.caught_transactions.length)})
                  </p>
                  <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
                    <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border)' }}>
                          {['Settlement ID', 'Amount', 'Confidence', 'Naive', 'Risk Policy'].map(h => (
                            <th key={h} style={{ textAlign: 'left', padding: '7px 10px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {comparison.caught_transactions.slice(0, 5).map((t, i) => (
                          <tr key={i} className="rq-row" style={{ borderTop: '1px solid var(--border-light)' }}>
                            <td style={{ padding: '7px 10px', fontFamily: 'monospace', fontSize: 11, color: 'var(--text-primary)' }}>{t.settlement_id}</td>
                            <td style={{ padding: '7px 10px', fontWeight: 600, color: 'var(--text-primary)' }}>₹{t.amount_rupees.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                            <td style={{ padding: '7px 10px', color: 'var(--text-secondary)' }}>{(t.confidence * 100).toFixed(1)}%</td>
                            <td style={{ padding: '7px 10px', color: 'var(--accent-red)', fontWeight: 600 }}>Cleared</td>
                            <td style={{ padding: '7px 10px', color: 'var(--accent-green)', fontWeight: 600 }}>Review</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Upload / collapsed nav */}
      {showUpload ? (
        <Card padding={0}>
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', background: 'var(--bg-subtle)', borderTopLeftRadius: 10, borderTopRightRadius: 10 }}>
            <button
              onClick={() => setSourceTab('csv')}
              className="rq-btn"
              style={{
                flex: 1, padding: '14px 20px', border: 'none', background: 'transparent', cursor: 'pointer',
                fontSize: 13, fontWeight: 600, color: sourceTab === 'csv' ? 'var(--accent-blue)' : 'var(--text-secondary)',
                borderBottom: `2px solid ${sourceTab === 'csv' ? 'var(--accent-blue)' : 'transparent'}`,
              }}>
              ERP / CSV Upload
            </button>
            <button
              onClick={() => setSourceTab('api')}
              className="rq-btn"
              style={{
                flex: 1, padding: '14px 20px', border: 'none', background: 'transparent', cursor: 'pointer',
                fontSize: 13, fontWeight: 600, color: sourceTab === 'api' ? 'var(--accent-blue)' : 'var(--text-secondary)',
                borderBottom: `2px solid ${sourceTab === 'api' ? 'var(--accent-blue)' : 'transparent'}`,
              }}>
              Direct Razorpay API Sync
            </button>
          </div>

          <div style={{ padding: '18px 20px' }}>
            {sourceTab === 'csv' ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
                  <Database size={14} color="var(--accent-blue)" />
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Upload batch CSV files</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>or use the 154-record benchmark dataset</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 14 }}>
                  <UploadZone label="Settlement Report" sublabel="Gateway export CSV" file={files.settlement} error={fileErrors.settlement} onChange={f => setFile('settlement', f)} />
                  <UploadZone label="Internal Ledger"   sublabel="Accounting ledger CSV" file={files.ledger} error={fileErrors.ledger} onChange={f => setFile('ledger', f)} />
                  <UploadZone label="Bank Statement"    sublabel="Bank account CSV" file={files.bank} error={fileErrors.bank} onChange={f => setFile('bank', f)} optional />
                </div>
              </>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                  <Database size={14} color="var(--accent-blue)" />
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Fetch Live Settlements via API</span>
                </div>
                <div style={{ background: '#f8fafc', border: '1px solid var(--border)', borderRadius: 8, padding: '20px', textAlign: 'center', marginBottom: 14 }}>
                  {apiStatus?.configured ? (
                    <>
                      <CheckCircle2 size={24} color="var(--accent-green)" style={{ margin: '0 auto 10px' }} />
                      <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                        Connected to Razorpay {apiStatus.mode === 'test' ? 'Test' : 'Live'} API
                      </p>
                      <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)' }}>
                        Key ID: <span style={{ fontFamily: 'monospace' }}>{apiStatus.key_id_prefix}</span>
                      </p>
                      <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--text-secondary)' }}>
                        Clicking Run will fetch the latest real settlements directly from Razorpay and map them against a sample ERP ledger.
                      </p>
                    </>
                  ) : (
                    <>
                      <UploadCloud size={24} color="var(--text-muted)" style={{ margin: '0 auto 10px' }} />
                      <p style={{ margin: '0 0 4px', fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>API Not Configured</p>
                      <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)' }}>
                        Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to your .env file to enable live sync.
                      </p>
                    </>
                  )}
                </div>

                {noSettlements && (
                  <Card padding="14px 16px" style={{ background: 'var(--accent-yellow-light)', border: '1px solid #fde68a', marginBottom: 14 }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                      <Info size={15} color="var(--accent-yellow)" style={{ flexShrink: 0, marginTop: 1 }} />
                      <div style={{ flex: 1 }}>
                        <p style={{ margin: '0 0 8px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{noSettlements}</p>
                        <Button size="sm" variant="primary" icon={Zap} onClick={() => { setSourceTab('csv'); setNoSettlements(null); }}>
                          Switch to Sample Data
                        </Button>
                      </div>
                    </div>
                  </Card>
                )}
              </>
            )}

            {loading && <PipelineBar stage={stage} />}
            {error && <p style={{ margin: '8px 0 0', fontSize: 12, color: 'var(--accent-red)', padding: '8px 10px', background: 'var(--accent-red-light)', borderRadius: 6 }}>{error}</p>}

            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <Button
                variant="primary" size="lg" icon={Play}
                onClick={() => handleRun(false)}
                disabled={loading || (sourceTab === 'api' && !apiStatus?.configured)}
              >
                {sourceTab === 'csv' ? 'Run Reconciliation' : 'Sync & Reconcile'}
              </Button>
              {sourceTab === 'csv' && (
                <Button variant="secondary" size="lg" onClick={() => handleRun(true)} disabled={loading}>
                  Use Sample Data
                </Button>
              )}
            </div>
          </div>
        </Card>
      ) : (
        <Card padding="12px 16px" style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <CheckCircle2 size={15} color="var(--accent-green)" />
          <span style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>
            Reconciliation complete
            <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>run {runId?.slice(0,8)}</span>
          </span>
          <button onClick={() => setShowUpload(true)} className="rq-btn" style={{ marginLeft: 6, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
            <RefreshCw size={11} /> Re-run
          </button>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <Button size="sm" variant="primary" onClick={() => navigate('/decisions')}>Decisions</Button>
            <Button size="sm" variant="secondary" onClick={() => navigate('/exceptions')}>Exceptions ({kpi?.human_review || 0})</Button>
            <Button size="sm" variant="secondary" onClick={() => navigate('/anomalies')}>Anomalies ({results?.anomalies?.length || 0})</Button>
          </div>
        </Card>
      )}

      {/* KPIs */}
      {loading && !results && (
        <>
          <SkeletonKPIGrid count={6} />
        </>
      )}
      {results && kpi && (
        <>
          <div className="rq-kpi-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12 }}>
            <KPICard title="Match Rate"     value={`${(kpi.match_rate * 100).toFixed(1)}%`}   subtitle={`${kpi.auto_matched} auto-cleared`}    icon={TrendingUp}   color="blue" />
            <KPICard title="Auto-Cleared"   value={fmtRupees(kpi.rupees_auto_cleared)}          subtitle="Processed instantly"                    icon={CheckCircle2} color="green" />
            <KPICard title="In Review"      value={fmtRupees(kpi.rupees_in_review)}             subtitle={`${kpi.human_review} items`}            icon={AlertCircle}  color="yellow" />
            <KPICard title="Unresolved"     value={kpi.unresolved}                              subtitle="Need investigation"                     icon={ShieldAlert}  color="red" />
            <KPICard title="Bank Confirmed" value={kpi.bank_confirmed || 0}                     subtitle="3-way matched"                          icon={Banknote}     color="purple" />
            <KPICard title="Leakage Found"  value={fmtRupees(results.leakage_report?.total_leakage_rupees || 0)} subtitle={`${results.anomalies?.length || 0} anomalies`} icon={ShieldAlert} color="red" />
          </div>

          {/* Charts */}
          <div className="rq-chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <Card padding="18px 20px">
              <p style={{ margin: '0 0 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Status Distribution</p>
              <div style={{ height: 200, display: 'flex', alignItems: 'center' }}>
                <ResponsiveContainer width="50%" height="100%">
                  <PieChart>
                    <Pie data={pieData} innerRadius={50} outerRadius={70} paddingAngle={3} dataKey="value" strokeWidth={0}>
                      {pieData.map((_, i) => <Cell key={i} fill={DONUT_COLORS[i]} />)}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 7, fontSize: 12, boxShadow: 'var(--shadow-md)' }}
                      formatter={(v, n) => [`${v} records`, n]}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {pieData.map((d, i) => (
                    <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: DONUT_COLORS[i], flexShrink: 0 }} />
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{d.name}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{d.value}</span>
                    </div>
                  ))}
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: 8, display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                    <span style={{ color: 'var(--text-muted)' }}>Total</span>
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{kpi.total_records}</span>
                  </div>
                </div>
              </div>
            </Card>

            <Card padding="18px 20px">
              <p style={{ margin: '0 0 14px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Volume by Amount Band</p>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={bandData} barCategoryGap="35%">
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 7, fontSize: 12, boxShadow: 'var(--shadow-md)' }}
                      cursor={{ fill: 'rgba(37,99,235,0.04)' }}
                      formatter={v => [`${v} settlements`]}
                    />
                    <Bar dataKey="count" radius={[4,4,0,0]}>
                      {bandData.map((_, i) => <Cell key={i} fill={i === 3 ? '#dc2626' : '#2563eb'} opacity={0.7 + i * 0.08} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          {/* Bank strip */}
          {kpi.bank_confirmed > 0 && (
            <Card padding="16px 20px">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                <Banknote size={14} color="var(--accent-purple)" />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>3-Way Bank Reconciliation</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
                {[
                  { label: 'Bank Confirmed', value: kpi.bank_confirmed, color: 'var(--accent-green)' },
                  { label: 'Discrepancies', value: results.matches?.filter(m => m.status === 'BANK_DISCREPANCY').length || 0, color: 'var(--accent-yellow)' },
                  { label: 'Funds in Transit', value: kpi.funds_in_transit, color: 'var(--accent-purple)' },
                  { label: 'Anomalies', value: results.anomalies?.length || 0, color: 'var(--accent-red)' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color, letterSpacing: -0.5 }}>{value}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{label}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Empty state */}
      {!results && !loading && (
        <div style={{ border: '1px dashed var(--border)', borderRadius: 10 }}>
          <EmptyState
            icon={Activity}
            title="No reconciliation run yet"
            subtitle={<>Upload your CSV files above or click <strong>Use Sample Data</strong> to get started.</>}
          />
        </div>
      )}
    </div>
  );
}
