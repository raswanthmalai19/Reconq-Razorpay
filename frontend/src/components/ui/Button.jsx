const VARIANTS = {
  primary:   { bg: 'var(--accent-blue)',        color: '#fff',               border: 'transparent' },
  secondary: { bg: '#ffffff',                   color: 'var(--text-primary)', border: 'var(--border)' },
  ghost:     { bg: 'transparent',                color: 'var(--text-secondary)', border: 'transparent' },
  success:   { bg: 'var(--accent-green-light)', color: 'var(--accent-green)', border: '#bbf7d0' },
  danger:    { bg: 'var(--accent-red-light)',   color: 'var(--accent-red)',   border: '#fecaca' },
  purple:    { bg: 'var(--accent-purple-light)',color: 'var(--accent-purple)', border: '#ddd6fe' },
};

const SIZES = {
  sm: { padding: '6px 12px', fontSize: 12, radius: 6, gap: 5 },
  md: { padding: '8px 16px', fontSize: 13, radius: 7, gap: 6 },
  lg: { padding: '10px 20px', fontSize: 13, radius: 8, gap: 7 },
};

export default function Button({
  children, variant = 'secondary', size = 'md', icon: Icon,
  disabled, loading, style, ...props
}) {
  const v = VARIANTS[variant] || VARIANTS.secondary;
  const s = SIZES[size] || SIZES.md;
  const isDisabled = disabled || loading;

  return (
    <button
      className="rq-btn"
      disabled={isDisabled}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: s.gap,
        padding: s.padding, borderRadius: s.radius,
        border: `1px solid ${v.border}`, background: v.bg, color: v.color,
        fontSize: s.fontSize, fontWeight: 600, fontFamily: 'inherit',
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        opacity: isDisabled ? 0.55 : 1,
        whiteSpace: 'nowrap',
        ...style,
      }}
      {...props}
    >
      {Icon && !loading && <Icon size={s.fontSize + 1} />}
      {loading && (
        <svg className="rq-spin" width={s.fontSize + 1} height={s.fontSize + 1} viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
          <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </svg>
      )}
      {children}
    </button>
  );
}
