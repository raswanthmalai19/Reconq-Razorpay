import Button from './Button';

export default function EmptyState({ icon: Icon, title, subtitle, action, actionLabel, onAction, tone = 'muted' }) {
  const iconColor = tone === 'success' ? 'var(--accent-green)' : tone === 'warning' ? 'var(--accent-yellow)' : 'var(--text-muted)';
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      textAlign: 'center', padding: '48px 24px', gap: 6,
    }}>
      {Icon && <Icon size={32} color={iconColor} style={{ marginBottom: 8 }} />}
      {title && <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</p>}
      {subtitle && <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)', maxWidth: 380, lineHeight: 1.5 }}>{subtitle}</p>}
      {(action || (actionLabel && onAction)) && (
        <div style={{ marginTop: 10 }}>
          {action || <Button variant="primary" onClick={onAction}>{actionLabel}</Button>}
        </div>
      )}
    </div>
  );
}
