export function Input({ icon: Icon, style, ...props }) {
  return (
    <div style={{ position: 'relative', ...style }}>
      {Icon && <Icon size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />}
      <input
        {...props}
        style={{
          width: '100%', boxSizing: 'border-box',
          paddingLeft: Icon ? 32 : 12, paddingRight: 12, paddingTop: 8, paddingBottom: 8,
          borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
          background: '#fff', fontSize: 13, color: 'var(--text-primary)',
          outline: 'none', fontFamily: 'inherit',
        }}
      />
    </div>
  );
}

export function TextArea({ style, ...props }) {
  return (
    <textarea
      {...props}
      style={{
        width: '100%', boxSizing: 'border-box',
        borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
        background: 'var(--bg-subtle)', color: 'var(--text-primary)',
        padding: '10px 12px', fontSize: 13, resize: 'vertical',
        outline: 'none', fontFamily: 'inherit', lineHeight: 1.5,
        ...style,
      }}
    />
  );
}

export function Select({ style, children, ...props }) {
  return (
    <select
      {...props}
      style={{
        paddingLeft: 12, paddingRight: 30, paddingTop: 8, paddingBottom: 8,
        borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
        background: '#fff', fontSize: 13, color: 'var(--text-primary)',
        outline: 'none', cursor: 'pointer', fontFamily: 'inherit',
        appearance: 'none',
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%239c9ca6' stroke-width='1.5' fill='none'/%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 10px center',
        ...style,
      }}
    >
      {children}
    </select>
  );
}
