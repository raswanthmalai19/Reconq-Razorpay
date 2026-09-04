import Card from './ui/Card';

const COLORS = {
  blue:   { icon: '#2563eb', bg: '#eff6ff' },
  green:  { icon: '#16a34a', bg: '#f0fdf4' },
  red:    { icon: '#dc2626', bg: '#fef2f2' },
  yellow: { icon: '#ca8a04', bg: '#fefce8' },
  purple: { icon: '#7c3aed', bg: '#f5f3ff' },
};

export default function KPICard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  const c = COLORS[color] || COLORS.blue;

  return (
    <Card hover padding="16px 18px">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {title}
        </span>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: c.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon size={14} color={c.icon} />
        </div>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: -0.5 }}>{value}</div>
      {subtitle && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{subtitle}</div>
      )}
    </Card>
  );
}
