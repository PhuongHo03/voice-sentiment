import { useState } from 'react';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';

interface Props {
  loading: boolean;
  onAudio: (file: File) => void;
  onText: (text: string) => void;
}

export function AudioInputPanel({ loading, onAudio, onText }: Props) {
  const [text, setText] = useState('');
  const { recording, start, stop } = useAudioRecorder();

  async function toggleRecording() {
    if (recording) onAudio(await stop()); else await start();
  }

  return <section className="card">
    <h2>Input & Playback</h2>
    <input type="file" accept="audio/mp3,audio/mpeg,audio/wav,audio/mp4,video/mp4,.mp4" disabled={loading} onChange={(event) => event.target.files?.[0] && onAudio(event.target.files[0])} />
    <button disabled={loading} onClick={toggleRecording}>{recording ? 'Dừng ghi âm' : 'Ghi âm trực tiếp'}</button>
    <textarea placeholder="Test nhanh bằng transcript text..." value={text} onChange={(event) => setText(event.target.value)} />
    <button disabled={loading || !text.trim()} onClick={() => onText(text)}>Phân tích text</button>
  </section>;
}
