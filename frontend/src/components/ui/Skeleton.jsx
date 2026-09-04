export function SkeletonBlock({ width = '100%', height = 16, radius = 6, style }) {
  return <div className="rq-skeleton" style={{ width, height, borderRadius: radius, ...style }} />;
}

export function SkeletonKPIGrid({ count = 6 }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${count}, 1fr)`, gap: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 18px' }}>
          <SkeletonBlock width="60%" height={11} style={{ marginBottom: 14 }} />
          <SkeletonBlock width="45%" height={22} style={{ marginBottom: 8 }} />
          <SkeletonBlock width="70%" height={11} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonRows({ rows = 5, cols = 5 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 16 }}>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} style={{ display: 'flex', gap: 16 }}>
          {Array.from({ length: cols }).map((_, c) => (
            <SkeletonBlock key={c} width={c === 0 ? '18%' : `${100 / cols}%`} height={14} />
          ))}
        </div>
      ))}
    </div>
  );
}
