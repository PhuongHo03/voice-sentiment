import type { TranscriptTurn } from '../../types/analysis';

type TranscriptRole = 'employee' | 'customer' | 'system';

export function TranscriptLog({ turns }: { turns: TranscriptTurn[] }) {
  function getSpeakerRole(speaker?: string): TranscriptRole {
    const speakerName = (speaker || '').toLowerCase();
    if (
      speakerName.includes('hệ thống') ||
      speakerName.includes('system') ||
      speakerName.includes('ivr')
    ) {
      return 'system';
    }

    if (
      speakerName.includes('nhân viên') ||
      speakerName.includes('agent') ||
      speakerName.includes('speaker 1')
    ) {
      return 'employee';
    }

    return 'customer';
  }

  return (
    <section className="card">
      <h2>Transcript</h2>
      {turns.length === 0 ? (
        <p>Chưa có transcript.</p>
      ) : (
        <div className="transcript-dialogue">
          {turns.map((turn, index) => {
            const role = getSpeakerRole(turn.speaker);
            const fallbackSpeaker = role === 'employee' ? 'Nhân viên' : role === 'system' ? 'Hệ thống' : 'Khách hàng';

            return (
              <div className={`transcript-turn ${role}`} key={index}>
                <strong>{turn.speaker || fallbackSpeaker}:</strong>
                <p>{turn.text}</p>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
