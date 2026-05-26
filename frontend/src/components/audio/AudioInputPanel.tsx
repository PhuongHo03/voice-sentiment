import { useState, useRef } from 'react';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';

interface Props {
  loading: boolean;
  disabled?: boolean;
  onAudio: (file: File) => void;
  onText: (text: string) => void;
}

export function AudioInputPanel({ loading, disabled = false, onAudio, onText }: Props) {
  const [text, setText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { recording, start, stop } = useAudioRecorder();

  const isLocked = loading || disabled;

  async function toggleRecording() {
    if (recording) onAudio(await stop()); else await start();
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  }

  function handleAnalyzeFile() {
    if (selectedFile) {
      onAudio(selectedFile);
    }
  }

  function handleCancelFile() {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  return (
    <section className="card">
      <h2>Input & Playback</h2>
      
      {/* Hidden native file input */}
      <input
        type="file"
        ref={fileInputRef}
        accept="audio/mp3,audio/mpeg,audio/wav,audio/mp4,video/mp4,.mp4"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        disabled={isLocked}
      />

      {/* Custom Premium File Upload UI */}
      {selectedFile === null ? (
        <button
          type="button"
          disabled={isLocked}
          onClick={() => fileInputRef.current?.click()}
          style={{
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
          }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-upload"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
          Tải lên file âm thanh
        </button>
      ) : (
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
          <div style={{
            fontSize: '0.85rem',
            color: 'var(--text-muted)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '10px 14px',
            borderRadius: '12px',
            border: '1px dashed var(--glass-border)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-file-text" style={{ flexShrink: 0 }}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              File: <strong>{selectedFile.name}</strong>
            </span>
          </div>
          <div style={{ display: 'flex', gap: '12px', width: '100%' }}>
            <button
              type="button"
              disabled={isLocked}
              onClick={handleAnalyzeFile}
              style={{
                flex: 1,
                margin: 0,
                background: 'linear-gradient(135deg, var(--color-primary) 0%, #7c3aed 100%)',
                boxShadow: '0 4px 12px var(--color-primary-glow)'
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-activity"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
              Phân tích
            </button>
            <button
              type="button"
              disabled={isLocked}
              onClick={handleCancelFile}
              style={{
                flex: 1,
                margin: 0,
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-x"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              Hủy
            </button>
          </div>
        </div>
      )}

      <button disabled={isLocked} onClick={toggleRecording}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-mic"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
        {recording ? 'Dừng ghi âm' : 'Ghi âm trực tiếp'}
      </button>
      
      <textarea
        placeholder="Test nhanh bằng transcript text..."
        value={text}
        onChange={(event) => setText(event.target.value)}
        disabled={isLocked}
      />
      
      <button disabled={isLocked || !text.trim()} onClick={() => onText(text)}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-file-text"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        Phân tích text
      </button>
    </section>
  );
}
