export default function Card({ children, style, hover, padding = 0, ...props }) {
  return (
    <div
      className={hover ? 'rq-card-hover' : ''}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-lg)',
        boxShadow: 'var(--shadow-sm)',
        padding,
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
}
