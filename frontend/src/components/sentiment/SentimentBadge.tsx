export function SentimentBadge({ sentiment, reason, confidence }: { sentiment?: string; reason?: string; confidence?: number }) {
  const icon = sentiment === 'negative' ? '😡' : sentiment === 'positive' ? '😊' : '😐';
  return <section className="card"><h2>Sentiment</h2><div className={`sentiment ${sentiment ?? 'neutral'}`}>{icon} {sentiment ?? 'pending'}</div>{reason && <p>{reason}</p>}{confidence !== undefined && <small>Confidence: {Math.round(confidence * 100)}%</small>}</section>;
}
