import { useEffect } from 'react';
import { SessionDetailPanel, type SessionDetailData } from './SessionDetailPanel';

interface SessionDetailModalProps {
  session: SessionDetailData;
  onClose: () => void;
}

export function SessionDetailModal({ session, onClose }: SessionDetailModalProps) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose();
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div className="session-detail-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="session-detail-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="session-detail-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="session-detail-modal-header">
          <div>
            <span className="session-detail-eyebrow">Chi tiết phiên làm việc</span>
            <h2 id="session-detail-modal-title">{session.name || 'Không có tiêu đề'}</h2>
          </div>
          <button className="close-overlay-btn" onClick={onClose} aria-label="Đóng chi tiết phiên">
            &times;
          </button>
        </header>

        <div className="session-detail-modal-body">
          <SessionDetailPanel session={session} variant="inline" />
        </div>
      </div>
    </div>
  );
}
