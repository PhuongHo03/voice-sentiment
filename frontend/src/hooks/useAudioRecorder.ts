import { useRef, useState } from 'react';

export function useAudioRecorder() {
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false);

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunksRef.current = [];
    recorderRef.current = new MediaRecorder(stream);
    recorderRef.current.ondataavailable = (event) => chunksRef.current.push(event.data);
    recorderRef.current.start();
    setRecording(true);
  }

  function stop(): Promise<File> {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder) throw new Error('Recorder is not active');
      recorder.onstop = () => {
        recorder.stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setRecording(false);
        resolve(new File([blob], 'recording.webm', { type: 'audio/webm' }));
      };
      recorder.stop();
    });
  }

  return { recording, start, stop };
}
