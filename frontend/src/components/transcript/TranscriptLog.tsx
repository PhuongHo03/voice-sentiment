import type { TranscriptTurn } from '../../types/analysis';

export function TranscriptLog({ turns }: { turns: TranscriptTurn[] }) {
  return (
    <section className="card">
      <h2>Transcript</h2>
      {turns.length === 0 ? (
        <p>Chưa có transcript.</p>
      ) : (
        turns.map((turn, index) => {
          const speakerName = (turn.speaker || '').toLowerCase();
          const isEmployee = speakerName.includes('nhân viên') || speakerName.includes('speaker 1');
          
          return (
            <div className={`bubble ${isEmployee ? 'employee' : 'customer'}`} key={index}>
              <strong>{turn.speaker}</strong>
              <p>{turn.text}</p>
            </div>
          );
        })
      )}
    </section>
  );
}
