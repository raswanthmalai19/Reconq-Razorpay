import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export const reconcileFiles = async (settlementFile, ledgerFile, bankFile = null) => {
  const form = new FormData();
  form.append('settlement', settlementFile);
  form.append('ledger', ledgerFile);
  if (bankFile) form.append('bank_statement', bankFile);
  const { data } = await api.post('/reconcile', form);
  return data;
};

export const reconcileSample = async () => {
  const { data } = await api.post('/reconcile/sample');
  return data;
};

export const syncRazorpay = async () => {
  const { data } = await api.post('/razorpay/sync');
  if (data.error) throw new Error(data.error);
  return data;
};

export const getRazorpayStatus = async () => {
  const { data } = await api.get('/razorpay/status');
  return data;
};

export const getComparison = async (settlementFile = null, ledgerFile = null) => {
  const form = new FormData();
  if (settlementFile) form.append('settlement', settlementFile);
  if (ledgerFile) form.append('ledger', ledgerFile);
  const { data } = await api.post('/reconcile/compare', form);
  return data;
};

export const getResults = async (runId) => {
  const { data } = await api.get(`/results/${runId}`);
  return data;
};

export const exportCsv = async (runId) => {
  const { data } = await api.get(`/results/${runId}/export`, { responseType: 'blob' });
  return data;
};

export const sendCopilotMessage = async (message, runId = 'default') => {
  const { data } = await api.post('/copilot/chat', { message, run_id: runId });
  return data;
};

export const submitOverride = async (settlementId, decision, note = '') => {
  const { data } = await api.post('/override', { settlement_id: settlementId, decision, note });
  return data;
};

export const getAnomalies = async (runId) => {
  const { data } = await api.get(`/anomalies/${runId}`);
  return data;
};

export const getAuditLog = async (runId) => {
  const { data } = await api.get(`/audit/${runId}`);
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('/health');
  return data;
};

// ── Suggested Fix ────────────────────────────────────────────────────
// Generate a fix proposal for a reconciliation exception.
// The proposal is cross-checked against the evidence before returning.
export const getSuggestedFix = async (exceptionData) => {
  const { data } = await api.post('/suggested-fix/generate', exceptionData);
  return data;
};

// Log a human-approved fix to the audit trail.
// Nothing is sent externally — audit log only.
export const approveSuggestedFix = async (settlementId, runId, fixProposal) => {
  const { data } = await api.post('/suggested-fix/approve', {
    settlement_id: settlementId,
    run_id: runId,
    fix_proposal: fixProposal,
  });
  return data;
};
