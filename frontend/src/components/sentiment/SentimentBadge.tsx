export function SentimentBadge({ sentiment, reason, confidence }: { sentiment?: string; reason?: string; confidence?: number }) {
  const s = (sentiment || '').toLowerCase();
  const icon = s === 'negative' ? '😡' : s === 'positive' ? '😊' : '😐';
  const label = s === 'positive' ? 'Tích cực' : s === 'negative' ? 'Tiêu cực' : s === 'neutral' ? 'Trung lập' : 'Chờ...';
  return (
    <section className="card">
      <h2>Sắc thái cuộc gọi</h2>
      <div className={`sentiment ${s || 'neutral'}`}>{icon} {label}</div>
      {reason && <p style={{ marginTop: '12px' }}>{reason}</p>}
      {confidence !== undefined && <small>Độ tin cậy: {Math.round(confidence * 100)}%</small>}
    </section>
  );
}
