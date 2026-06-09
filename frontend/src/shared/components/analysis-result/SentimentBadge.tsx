export function SentimentBadge({ sentiment, reason, confidence }: { sentiment?: string; reason?: string; confidence?: number | null }) {
  const s = (sentiment || '').toLowerCase();
  const icon = s === 'negative' ? '😡' : s === 'positive' ? '😊' : '😐';
  const label = s === 'positive' ? 'Tích cực' : s === 'negative' ? 'Tiêu cực' : s === 'neutral' ? 'Trung lập' : 'Chờ...';
  return (
    <section className="card">
      <h2>Sắc thái cuộc gọi</h2>
      <div className={`sentiment ${s || 'neutral'}`}>{icon} {label}</div>
      <p style={{ marginTop: '12px' }}>{reason || 'Chưa có phân tích sắc thái.'}</p>
      <small>
        Độ tin cậy: {confidence !== undefined && confidence !== null ? `${Math.round(confidence * 100)}%` : 'Chưa có'}
      </small>
    </section>
  );
}
