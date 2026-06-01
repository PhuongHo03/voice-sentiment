import { useState, useRef } from 'react';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';

interface Props {
  loading: boolean;
  disabled?: boolean;
  /** Called when user clicks "Phân tích" — receives the already-uploaded object_key and file name */
  onAudioFromKey: (objectKey: string, fileName: string) => void;
  onText: (text: string) => void;
  /** Called to upload a file to MinIO immediately (returns object_key) */
  onUploadFile: (file: File) => Promise<{ object_key: string; original_name: string | null }>;
}

interface PendingFile {
  file: File;
  objectKey: string;
  uploading: boolean;
  uploadError: string | null;
}

export function AudioInputPanel({ loading, disabled = false, onAudioFromKey, onText, onUploadFile }: Props) {
  const [text, setText] = useState('');
  const [pending, setPending] = useState<PendingFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { recording, start, stop } = useAudioRecorder();

  const isLocked = loading || disabled;

  /** Shared upload logic: upload file to MinIO immediately, set pending state */
  async function uploadAndPend(file: File) {
    const uploading: PendingFile = { file, objectKey: '', uploading: true, uploadError: null };
    setPending(uploading);
    try {
      const result = await onUploadFile(file);
      setPending({ file, objectKey: result.object_key, uploading: false, uploadError: null });
    } catch (e) {
      setPending(prev => prev ? { ...prev, uploading: false, uploadError: e instanceof Error ? e.message : 'Lỗi tải lên' } : null);
    }
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    await uploadAndPend(file);
  }

  async function toggleRecording() {
    if (recording) {
      const file = await stop();
      await uploadAndPend(file);
    } else {
      setPending(null);
      await start();
    }
  }

  function handleAnalyze() {
    if (!pending || pending.uploading || !pending.objectKey) return;
    onAudioFromKey(pending.objectKey, pending.file.name);
    setPending(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function handleCancelFile() {
    setPending(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  const isRecordedFile = pending?.file.name === 'recording.webm';

  return (
    <section className="card">
      <h2>Input &amp; Playback</h2>

      {/* Hidden native file input */}
      <input
        type="file"
        ref={fileInputRef}
        accept="audio/mp3,audio/mpeg,audio/wav,audio/mp4,video/mp4,.mp4"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        disabled={isLocked}
      />

      {/* File Upload Button (shown when nothing selected) */}
      {pending === null ? (
        <button
          type="button"
          disabled={isLocked}
          onClick={() => fileInputRef.current?.click()}
          style={{
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
          }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
          Tải lên file âm thanh
        </button>
      ) : (
        /* File selected / uploading / ready-to-analyze panel */
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
          {/* File info row */}
          <div style={{
            fontSize: '0.85rem',
            overflow: 'hidden',
            background: pending.uploadError
              ? 'rgba(244, 63, 94, 0.06)'
              : pending.uploading
                ? 'rgba(255, 255, 255, 0.04)'
                : isRecordedFile
                  ? 'rgba(16, 185, 129, 0.08)'
                  : 'rgba(255, 255, 255, 0.04)',
            padding: '10px 14px',
            borderRadius: '12px',
            border: pending.uploadError
              ? '1px dashed rgba(244,63,94,0.4)'
              : pending.uploading
                ? '1px dashed var(--glass-border)'
                : isRecordedFile
                  ? '1px dashed rgba(16, 185, 129, 0.4)'
                  : '1px dashed var(--glass-border)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {/* Icon */}
            {pending.uploading ? (
              /* Spinner */
              <div style={{ width: '14px', height: '14px', border: '2px solid rgba(255,255,255,0.15)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', flexShrink: 0, animation: 'spin 0.8s linear infinite' }} />
            ) : isRecordedFile ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
            )}

            {/* Label */}
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, color: pending.uploadError ? 'var(--color-rose)' : isRecordedFile ? '#10b981' : 'var(--text-muted)' }}>
              {pending.uploading
                ? <><strong>Đang lưu...</strong> {pending.file.name}</>
                : pending.uploadError
                  ? <><strong>Lỗi:</strong> {pending.uploadError}</>
                  : <>{isRecordedFile ? '🎙️ Ghi âm: ' : 'File: '}<strong>{pending.file.name}</strong></>
              }
            </span>

            {/* Saved badge */}
            {!pending.uploading && !pending.uploadError && (
              <span style={{ fontSize: '0.72rem', color: '#10b981', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: '99px', padding: '2px 8px', whiteSpace: 'nowrap', flexShrink: 0 }}>
                ✓ Đã lưu
              </span>
            )}
          </div>

          {/* Analyze / Cancel buttons */}
          <div style={{ display: 'flex', gap: '12px', width: '100%' }}>
            <button
              type="button"
              disabled={isLocked || pending.uploading || !!pending.uploadError || !pending.objectKey}
              onClick={handleAnalyze}
              style={{
                flex: 1,
                margin: 0,
                background: 'linear-gradient(135deg, var(--color-primary) 0%, #7c3aed 100%)',
                boxShadow: '0 4px 12px var(--color-primary-glow)'
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
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
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              Hủy
            </button>
          </div>
        </div>
      )}

      {/* Record button */}
      <button
        disabled={isLocked || (pending !== null && !recording)}
        onClick={toggleRecording}
        style={recording ? {
          background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
          boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)',
          animation: 'pulse-glow 1.5s infinite'
        } : undefined}
      >
        {recording ? (
          <>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="0"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            Dừng ghi âm
          </>
        ) : (
          <>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
            Ghi âm trực tiếp
          </>
        )}
      </button>

      <textarea
        placeholder="Test nhanh bằng transcript text..."
        value={text}
        onChange={(event) => setText(event.target.value)}
        disabled={isLocked}
      />

      <button disabled={isLocked || !text.trim()} onClick={() => onText(text)}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        Phân tích text
      </button>
    </section>
  );
}
