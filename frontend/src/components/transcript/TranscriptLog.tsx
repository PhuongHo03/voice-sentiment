import type { TranscriptTurn } from '../../types/analysis';

export function TranscriptLog({ turns }: { turns: TranscriptTurn[] }) {
  return <section className="card"><h2>Transcript</h2>{turns.length === 0 ? <p>Chưa có transcript.</p> : turns.map((turn, index) => <div className="bubble" key={index}><strong>{turn.speaker}</strong><p>{turn.text}</p></div>)}</section>;
}
