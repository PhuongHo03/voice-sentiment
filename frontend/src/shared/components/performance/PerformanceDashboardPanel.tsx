import type { ReactNode } from 'react';

export interface PerformanceStats {
  total_jobs?: number | null;
  average_confidence?: number | null;
  average_agent_score?: number | null;
  sentiment_distribution?: {
    positive?: number | null;
    neutral?: number | null;
    negative?: number | null;
  } | null;
  weekly_trends?: Array<{ date: string; count: number }> | null;
}

export interface PerformanceSessionItem {
  job_id: string;
  name?: string | null;
  status?: string | null;
  input_type?: string | null;
  created_at?: string | null;
  sentiment?: string | null;
  agent_score?: number | null;
}

export interface PerformanceProfile {
  title: string;
  subtitle?: string | null;
  avatarText?: string;
  eyebrow?: string;
}

interface PerformanceDashboardPanelProps {
  stats?: PerformanceStats | null;
  sessions?: PerformanceSessionItem[];
  profile?: PerformanceProfile;
  loading?: boolean;
  compact?: boolean;
  onClose?: () => void;
  onSessionClick?: (session: PerformanceSessionItem) => void;
}

function getDominantSentiment(dist?: PerformanceStats['sentiment_distribution']): string {
  const pos = dist?.positive ?? 0;
  const neu = dist?.neutral ?? 0;
  const neg = dist?.negative ?? 0;
  if (pos === 0 && neu === 0 && neg === 0) return 'Chưa có';
  if (pos >= neu && pos >= neg) return 'Tích cực';
  if (neu >= pos && neu >= neg) return 'Trung lập';
  return 'Tiêu cực';
}

function getSentimentLabel(sentiment?: string | null): string {
  const normalized = sentiment?.toLowerCase();
  if (normalized === 'positive') return 'Tích cực';
  if (normalized === 'negative') return 'Tiêu cực';
  if (normalized === 'neutral') return 'Trung lập';
  if (normalized === 'pending') return 'Đang chờ';
  if (normalized === 'processing') return 'Đang xử lý';
  if (normalized === 'failed') return 'Thất bại';
  return 'Chưa có';
}

function formatDate(value?: string | null): string {
  if (!value) return '';
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  return new Date(timestamp).toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

function shortDate(value: string): string {
  const parts = value.split('-');
  if (parts.length === 3) return `${parts[2]}/${parts[1]}`;
  return value;
}

function MetricCard({ tone, label, value, subtext }: { tone: string; label: string; value: ReactNode; subtext: ReactNode }) {
  return (
    <div className={`metric-card ${tone}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      <div className="metric-subtext">{subtext}</div>
    </div>
  );
}

export function PerformanceDashboardPanel({
  stats,
  sessions = [],
  profile,
  loading = false,
  compact = false,
  onClose,
  onSessionClick,
}: PerformanceDashboardPanelProps) {
  const pos = stats?.sentiment_distribution?.positive ?? 0;
  const neu = stats?.sentiment_distribution?.neutral ?? 0;
  const neg = stats?.sentiment_distribution?.negative ?? 0;
  const totalSentiment = pos + neu + neg;
  const totalJobs = stats?.total_jobs ?? sessions.length ?? 0;
  const averageConfidence = stats?.average_confidence ?? 0;
  const averageScore = stats?.average_agent_score ?? 0;
  const posPct = totalSentiment ? (pos / totalSentiment) * 100 : 0;
  const neuPct = totalSentiment ? (neu / totalSentiment) * 100 : 0;
  const negPct = totalSentiment ? (neg / totalSentiment) * 100 : 0;
  const circumference = 251.3;
  const posLen = (posPct / 100) * circumference;
  const neuLen = (neuPct / 100) * circumference;
  const negLen = (negPct / 100) * circumference;
  const trends = stats?.weekly_trends ?? [];
  const maxTrendCount = Math.max(...trends.map((item) => item.count), 1);

  if (loading) {
    return (
      <div className="session-status-progress">
        <div className="session-progress-spinner"></div>
        <div className="session-progress-text">Đang tải báo cáo thống kê tổng hợp...</div>
      </div>
    );
  }

  return (
    <section className={`performance-dashboard-panel ${compact ? 'compact' : ''}`}>
      {profile && (
        <header className="performance-profile-header">
          <span className="emp-avatar large">{profile.avatarText || profile.title.substring(0, 2).toUpperCase()}</span>
          <div>
            {profile.eyebrow && <span className="session-detail-eyebrow">{profile.eyebrow}</span>}
            <h2>{profile.title}</h2>
            {profile.subtitle && <p className="emp-meta-email">{profile.subtitle}</p>}
          </div>
          {onClose && (
            <button className="close-panel-btn" onClick={onClose} title="Đóng">
              x
            </button>
          )}
        </header>
      )}

      <div className="stats-grid">
        <MetricCard
          tone="primary"
          label="Tổng số cuộc phân tích"
          value={totalJobs}
          subtext="Phiên hoàn thành trong hệ thống"
        />
        <MetricCard
          tone="success"
          label="Độ tin cậy trung bình"
          value={totalJobs ? `${Math.round(averageConfidence * 100)}%` : '0%'}
          subtext="Mức độ tự tin trung bình của LLM"
        />
        <MetricCard
          tone="warning"
          label="Điểm nhân viên trung bình"
          value={
            <>
              {totalJobs ? averageScore : 0}
              <span className="metric-unit">/100</span>
            </>
          }
          subtext="Đánh giá chất lượng hỗ trợ"
        />
        <MetricCard
          tone="info"
          label="Sắc thái chủ đạo"
          value={getDominantSentiment(stats?.sentiment_distribution)}
          subtext="Sắc thái có tần suất cao nhất"
        />
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Tỉ lệ Phân bố Sắc thái (Sentiment Ratio)</h3>
          <div className="chart-card-content">
            {totalSentiment > 0 ? (
              <div className="donut-svg-container">
                <svg width="160" height="160" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="12" />
                  {neg > 0 && (
                    <circle className="donut-chart-circle" cx="50" cy="50" r="40" fill="none" stroke="var(--color-rose)" strokeWidth="12" strokeDasharray={`${negLen} ${circumference}`} strokeDashoffset={0} transform="rotate(-90 50 50)" />
                  )}
                  {neu > 0 && (
                    <circle className="donut-chart-circle" cx="50" cy="50" r="40" fill="none" stroke="var(--color-blue)" strokeWidth="12" strokeDasharray={`${neuLen} ${circumference}`} strokeDashoffset={-negLen} transform="rotate(-90 50 50)" />
                  )}
                  {pos > 0 && (
                    <circle className="donut-chart-circle" cx="50" cy="50" r="40" fill="none" stroke="var(--color-teal)" strokeWidth="12" strokeDasharray={`${posLen} ${circumference}`} strokeDashoffset={-(negLen + neuLen)} transform="rotate(-90 50 50)" />
                  )}
                  <text className="donut-center-text" x="50" y="47" fontSize="13" fontWeight="800">{totalSentiment}</text>
                  <text className="donut-center-text" x="50" y="60" fontSize="7" fontWeight="600" fill="var(--text-secondary)">SESSIONS</text>
                </svg>
                <div className="donut-legend">
                  <div className="donut-legend-item"><span className="legend-color-box positive" />Tích cực: <strong>{pos}</strong> ({Math.round(posPct)}%)</div>
                  <div className="donut-legend-item"><span className="legend-color-box neutral" />Trung lập: <strong>{neu}</strong> ({Math.round(neuPct)}%)</div>
                  <div className="donut-legend-item"><span className="legend-color-box negative" />Tiêu cực: <strong>{neg}</strong> ({Math.round(negPct)}%)</div>
                </div>
              </div>
            ) : (
              <span className="performance-empty-text">Chưa có dữ liệu phân tích</span>
            )}
          </div>
        </div>

        <div className="chart-card">
          <h3>Xu hướng cuộc gọi trong tuần (Weekly Trends)</h3>
          <div className="chart-card-content">
            {trends.length > 0 ? (
              <div className="bar-chart-container">
                <svg className="bar-svg" viewBox="0 0 450 200">
                  <defs>
                    <linearGradient id="barGradientShared" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#c084fc" stopOpacity="0.8" />
                      <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.3" />
                    </linearGradient>
                  </defs>
                  <line x1="30" y1="20" x2="430" y2="20" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                  <line x1="30" y1="70" x2="430" y2="70" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                  <line x1="30" y1="120" x2="430" y2="120" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                  <line x1="30" y1="170" x2="430" y2="170" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
                  {trends.map((item, index) => {
                    const x = 50 + index * 55;
                    const barHeight = (item.count / maxTrendCount) * 135;
                    const y = 170 - barHeight;
                    return (
                      <g key={`${item.date}-${index}`}>
                        <rect className="chart-bar-rect" x={x} y={y} width="32" height={barHeight} rx="4" fill="url(#barGradientShared)" />
                        <text x={x + 16} y={y - 6} textAnchor="middle" fill="#fff" fontSize="9" fontWeight="700" opacity={item.count > 0 ? 1 : 0.2}>{item.count}</text>
                        <text x={x + 16} y="188" textAnchor="middle" fill="var(--text-secondary)" fontSize="9" fontWeight="500">{shortDate(item.date)}</text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            ) : (
              <span className="performance-empty-text">Không có dữ liệu xu hướng</span>
            )}
          </div>
        </div>
      </div>

      <section className="performance-history-section">
        <h3>Lịch Sử Làm Việc</h3>
        {sessions.length === 0 ? (
          <p className="no-data-mini">Chưa có phiên phân tích nào.</p>
        ) : (
          <div className="performance-session-list">
            {sessions.map((session) => (
              <button
                key={session.job_id}
                className="performance-session-card"
                onClick={() => onSessionClick?.(session)}
              >
                <div>
                  <span className={`mini-badge ${session.input_type || 'unknown'}`}>{session.input_type === 'audio' ? 'Audio' : 'Text'}</span>
                  <h4>{session.name || 'Không có tiêu đề'}</h4>
                  {session.agent_score !== null && session.agent_score !== undefined && (
                    <strong>{session.agent_score}/100đ</strong>
                  )}
                </div>
                <div className="performance-session-meta">
                  <span>{formatDate(session.created_at)}</span>
                  <span className={`sentiment-badge-mini ${(session.sentiment || session.status || '').toLowerCase()}`}>
                    {session.sentiment ? getSentimentLabel(session.sentiment) : getSentimentLabel(session.status)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
