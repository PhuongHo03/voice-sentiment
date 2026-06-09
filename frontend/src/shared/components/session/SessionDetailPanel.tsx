import { SummaryCard } from '../analysis-result/SummaryCard';
import { SentimentBadge } from '../analysis-result/SentimentBadge';
import { TranscriptLog } from '../analysis-result/TranscriptLog';
import type { AnalysisResult, TranscriptTurn } from '../../types/analysis';

export interface SessionDetailResult extends Partial<Omit<AnalysisResult, 'transcript' | 'summary'>> {
  transcript?: TranscriptTurn[] | null;
  summary?: string[] | null;
}

export interface SessionDetailData {
  jobId: string;
  name?: string | null;
  status: string;
  inputType?: string | null;
  createdAt?: string | null;
  errorMessage?: string | null;
  audioUrl?: string | null;
  result?: SessionDetailResult | null;
}

interface SessionDetailPanelProps {
  session: SessionDetailData;
  variant?: 'inline' | 'modal';
  showHeader?: boolean;
  onCreateNewSession?: () => void;
  error?: string | null;
}

function getJobStatusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return 'Chờ trong hàng đợi';
    case 'processing':
      return 'Đang xử lý';
    case 'completed':
      return 'Đã hoàn thành';
    case 'failed':
      return 'Thất bại';
    default:
      return 'Không rõ trạng thái';
  }
}

function getAgentScoreLabel(score: number): string {
  if (score >= 80) return 'Xuất sắc';
  if (score >= 50) return 'Đạt yêu cầu';
  return 'Cần cải thiện';
}

function getAgentScoreColor(score: number): string {
  if (score >= 80) return '#10b981';
  if (score >= 50) return '#3b82f6';
  return '#ef4444';
}

function getInputTypeLabel(inputType?: string | null): string {
  if (inputType === 'audio') return 'Audio';
  if (inputType === 'text') return 'Text';
  return 'Không rõ nguồn';
}

function formatSessionDate(value?: string | null): string | null {
  if (!value) return null;
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  return new Date(timestamp).toLocaleString('vi-VN');
}

function AgentScoreCard({ score, advice, status }: { score?: number | null; advice?: string[] | null; status?: string }) {
  const hasScore = score !== null && score !== undefined;
  const resolvedAdvice = hasScore
    ? advice && advice.length > 0
      ? advice
      : ['Hội thoại diễn ra tốt đẹp, nhân viên ứng xử đúng mực và hỗ trợ khách hàng hiệu quả.']
    : advice && advice.length > 0
      ? advice
      : status === 'completed'
        ? ['Chưa có đánh giá do dữ liệu hội thoại không đủ để chấm điểm nhân viên.']
        : ['Kết quả đánh giá và khuyến nghị sẽ hiển thị sau khi job xử lý xong.'];

  return (
    <div className="agent-scorecard-card session-detail-scorecard">
      <div className="agent-scorecard-layout">
        <div className="agent-score-ring-container">
          {hasScore ? (
            <>
              <div className="agent-score-ring-svg">
                <svg width="150" height="150" viewBox="0 0 100 100" aria-hidden="true">
                  <circle className="ring-bg" cx="50" cy="50" r="42" />
                  <circle
                    className="ring-progress"
                    cx="50"
                    cy="50"
                    r="42"
                    stroke={getAgentScoreColor(score)}
                    strokeDasharray="263.9"
                    strokeDashoffset={263.9 - (score / 100) * 263.9}
                    style={{ filter: `drop-shadow(0 0 6px ${getAgentScoreColor(score)}80)` }}
                  />
                </svg>
                <div className="agent-score-text">
                  <span className="agent-score-number">{score}</span>
                  <span className="agent-score-label">Điểm số</span>
                </div>
              </div>
              <div className="agent-status-label" style={{ color: getAgentScoreColor(score) }}>
                {getAgentScoreLabel(score)}
              </div>
            </>
          ) : (
            <>
              <div className="agent-score-placeholder">
                <span className="agent-score-placeholder-main">--</span>
                <span className="agent-score-placeholder-sub">Điểm số</span>
              </div>
              <div className="agent-status-label pending-score">Chưa có điểm</div>
            </>
          )}
        </div>

        <div className="agent-advice-panel">
          <div className="agent-advice-title">Đánh giá & Khuyến nghị của AI cho Nhân viên</div>
          <div className="advice-list">
            {resolvedAdvice.map((item, index) => (
              <div className={`advice-item ${hasScore ? '' : 'muted'}`} key={`${item}-${index}`}>
                <span className="advice-icon" aria-hidden="true">
                  {hasScore ? '•' : '...'}
                </span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function AudioPlaybackCard({ audioUrl }: { audioUrl: string }) {
  return (
    <section className="card session-detail-audio-card">
      <div className="session-detail-audio-title">
        <div className="session-detail-audio-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <path d="M12 19v4" />
            <path d="M8 23h8" />
          </svg>
        </div>
        <div>
          <strong>Nghe lại ghi âm cuộc hội thoại</strong>
          <span>Vừa phát ghi âm vừa đối chiếu với transcript bên dưới</span>
        </div>
      </div>
      <div className="session-detail-audio-player">
        <audio controls src={audioUrl} />
      </div>
    </section>
  );
}

export function SessionDetailPanel({
  session,
  variant = 'inline',
  showHeader = false,
  onCreateNewSession,
  error,
}: SessionDetailPanelProps) {
  const result = session.result;
  const hasResult = Boolean(result);
  const formattedDate = formatSessionDate(session.createdAt);

  return (
    <section className={`session-detail-panel ${variant}`}>
      {showHeader && (
        <div className="session-detail-hero">
          <div>
            <span className="session-detail-eyebrow">Chi tiết phiên làm việc</span>
            <h2>{session.name || 'Không có tiêu đề'}</h2>
          </div>
          <div className="session-detail-meta-stack">
            <span className={`mini-badge ${session.inputType || 'unknown'}`}>{getInputTypeLabel(session.inputType)}</span>
            {formattedDate && <span>{formattedDate}</span>}
          </div>
        </div>
      )}

      <div className="status-header session-detail-status">
        <div className="status-title-section">
          <span className="status-label">Tiến độ Job:</span>
          <div className={`status-badge ${session.status}`}>
            <span className="status-indicator-dot"></span>
            {getJobStatusLabel(session.status)}
          </div>
        </div>
        <div className="job-id-tag">
          Job ID: <code>{session.jobId}</code>
        </div>
      </div>

      {(error || session.errorMessage) && (
        <div className="error-panel session-detail-error">{error || session.errorMessage}</div>
      )}

      {!hasResult && session.status !== 'completed' && session.status !== 'failed' && (
        <div className="card session-detail-empty">
          <h2>Kết quả phân tích</h2>
          <p>Job đang được xử lý. Nội dung chi tiết sẽ tự cập nhật khi hệ thống hoàn tất phân tích.</p>
        </div>
      )}

      <AgentScoreCard score={result?.agent_score} advice={result?.agent_advice} status={session.status} />

      <SentimentBadge
        sentiment={result?.sentiment}
        reason={result?.sentiment_reason}
        confidence={result?.confidence}
      />

      <SummaryCard
        items={result?.summary ?? []}
        detailedSummary={result?.detailed_summary}
        scoreBreakdown={result?.agent_score_breakdown}
        qualityNotes={result?.quality_notes}
      />

      {session.audioUrl && <AudioPlaybackCard audioUrl={session.audioUrl} />}

      <TranscriptLog turns={result?.transcript ?? []} />

      {onCreateNewSession && (
        <div className="session-completed-banner session-detail-completed-banner">
          <span className="session-completed-text">
            Phân tích hoàn tất. Hãy tạo mới session để nhận job phân tích tiếp theo.
          </span>
          <button className="session-completed-btn" onClick={onCreateNewSession}>
            Tạo session mới
          </button>
        </div>
      )}
    </section>
  );
}
