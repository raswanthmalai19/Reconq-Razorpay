export default function KPICard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  const colors = {
    blue: 'from-blue-500/20 to-blue-600/5 border-blue-500/30',
    green: 'from-emerald-500/20 to-emerald-600/5 border-emerald-500/30',
    red: 'from-red-500/20 to-red-600/5 border-red-500/30',
    yellow: 'from-amber-500/20 to-amber-600/5 border-amber-500/30',
    purple: 'from-purple-500/20 to-purple-600/5 border-purple-500/30',
  };
  return (
    <div className={`bg-gradient-to-br ${colors[color]} backdrop-blur-sm border rounded-xl p-5 transition-all hover:scale-[1.02]`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium" style={{color: 'var(--text-secondary)'}}>{title}</span>
        {Icon && <Icon size={20} style={{color: `var(--accent-${color})`}} />}
      </div>
      <div className="text-2xl font-bold" style={{color: 'var(--text-primary)'}}>{value}</div>
      {subtitle && <div className="text-xs mt-1" style={{color: 'var(--text-secondary)'}}>{subtitle}</div>}
    </div>
  );
}
