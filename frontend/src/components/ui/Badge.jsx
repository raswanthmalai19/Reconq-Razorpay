// Single source of truth for every status/severity/event color mapping used
// across Decisions, Exceptions, Anomalies, and AuditLog — previously duplicated
// four times with slightly different values in each file.
export const STATUS_STYLES = {
  AUTO_MATCHED:     { color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
  HUMAN_REVIEW:     { color: '#ca8a04', bg: '#fefce8', border: '#fef08a' },
  UNRESOLVED:       { color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  BANK_CONFIRMED:   { color: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe' },
  BANK_DISCREPANCY: { color: '#ca8a04', bg: '#fefce8', border: '#fef08a' },
  FUNDS_IN_TRANSIT: { color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
};

export const SEVERITY_STYLES = {
  CRITICAL: { color: '#991b1b', bg: '#fef2f2', border: '#fca5a5' },
  HIGH:     { color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  MEDIUM:   { color: '#ca8a04', bg: '#fefce8', border: '#fde68a' },
  LOW:      { color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
};

export const EVENT_STYLES = {
  EXACT_MATCH:       { color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
  DECISION:          { color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  GROUP_MATCH:       { color: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe' },
  OVERRIDE:          { color: '#ca8a04', bg: '#fefce8', border: '#fde68a' },
  RAZORPAY_API_SYNC: { color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
};

const DEFAULT_STYLE = { color: '#71717a', bg: '#f9f9f9', border: '#e4e4e7' };

export default function Badge({ label, styleMap = STATUS_STYLES, dot, size = 'md' }) {
  const s = styleMap[label] || DEFAULT_STYLE;
  const fontSize = size === 'sm' ? 10 : 11;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: size === 'sm' ? '2px 7px' : '3px 8px', borderRadius: 5,
      fontSize, fontWeight: 600,
      color: s.color, background: s.bg, border: `1px solid ${s.border}`,
      whiteSpace: 'nowrap',
    }}>
      {dot && <span style={{ width: 5, height: 5, borderRadius: '50%', background: s.color, flexShrink: 0 }} />}
      {label?.replace(/_/g, ' ')}
    </span>
  );
}
