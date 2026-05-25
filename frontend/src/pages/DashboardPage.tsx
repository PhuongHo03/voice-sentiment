import { AudioInputPanel } from '../components/audio/AudioInputPanel';
import { SentimentBadge } from '../components/sentiment/SentimentBadge';
import { SummaryCard } from '../components/summary/SummaryCard';
import { TranscriptLog } from '../components/transcript/TranscriptLog';
import { useAnalysis } from '../hooks/useAnalysis';

export function DashboardPage() {
  const { job, error, loading, analyzeAudio, analyzeText } = useAnalysis();
  const result = job?.result;

  return <div className="app-container">
    <header className="main-header">
      <div className="logo-section">
        <span className="live-indicator"></span>
        <h1>Voice Sentiment Console</h1>
        <span className="version-badge">Phase 2 E2E</span>
      </div>
      <p className="subtitle">Hệ thống phân tích giọng nói, tóm tắt và đánh giá sắc thái cảm xúc cuộc gọi tiếng Việt</p>
    </header>

    <main className="dashboard">
      <AudioInputPanel loading={loading} onAudio={analyzeAudio} onText={analyzeText} />
      
      <section className="insights">
        <div className="status-header">
          <div className="status-title-section">
            <span className="status-label">Tiến độ Job:</span>
            <div className={`status-badge ${job?.status ?? 'idle'}`}>
              <span className="status-indicator-dot"></span>
              {job?.status === 'pending' ? 'Đang xếp hàng...' : 
               job?.status === 'processing' ? 'Đang phân tích...' : 
               job?.status === 'completed' ? 'Đã hoàn thành' : 
               job?.status === 'failed' ? 'Gặp sự cố' : 'Sẵn sàng'}
            </div>
          </div>
          {job?.job_id && (
            <div className="job-id-tag">
              Job ID: <code>{job.job_id}</code>
            </div>
          )}
        </div>

        {error && <div className="error-panel">{error}</div>}
        
        <TranscriptLog turns={result?.transcript ?? []} />
        <SummaryCard items={result?.summary ?? []} />
        <SentimentBadge sentiment={result?.sentiment} reason={result?.sentiment_reason} confidence={result?.confidence} />
      </section>
    </main>
  </div>;
}

