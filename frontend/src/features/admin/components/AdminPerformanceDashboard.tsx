import React from 'react';
import type { Employee, EmployeeSession, EmployeeStats } from '../types/admin';
import { AdminRefreshButton } from './AdminRefreshButton';
import { getFilePresignedUrl } from '../../analysis/api/analysisApi';
import { PerformanceDashboardPanel } from '../../../shared/components/performance/PerformanceDashboardPanel';
import { SessionDetailModal } from '../../../shared/components/session/SessionDetailModal';
import type { SessionDetailData } from '../../../shared/components/session/SessionDetailPanel';
import type { JobStatus } from '../../../shared/types/analysis';

interface AdminPerformanceDashboardProps {
  employees: Employee[];
  selectedEmp: Employee | null;
  empStats: EmployeeStats | null;
  empSessions: EmployeeSession[];
  selectedSession: EmployeeSession | null;
  selectedSessionDetail: JobStatus | null;
  isSessionDetailLoading: boolean;
  handleSelectSession: (session: EmployeeSession) => void;
  closeSelectedSession: () => void;
  isLoading: boolean;
  isDetailsLoading: boolean;
  error: string | null;
  handleSelectEmployee: (employee: Employee) => void;
  totalEmployeesCount: number;
  totalEmployeeJobs: number;
  systemAvgScore: string;
  // current logged-in user id (optional) — used to mark and prioritize self
  currentUserId?: string;
  fetchEmployees: () => void;
}

export const AdminPerformanceDashboard: React.FC<AdminPerformanceDashboardProps> = (props) => {
  const {
    employees,
    selectedEmp,
    empStats,
    empSessions,
    selectedSession,
    selectedSessionDetail,
    isSessionDetailLoading,
    handleSelectSession,
    closeSelectedSession,
    isLoading,
    isDetailsLoading,
    error,
    handleSelectEmployee,
    totalEmployeesCount,
    totalEmployeeJobs,
    systemAvgScore,
    currentUserId,
    fetchEmployees,
  } = props;

  const selectedSessionViewModel: SessionDetailData | null = selectedSessionDetail
    ? {
        jobId: selectedSessionDetail.job_id,
        name: selectedSessionDetail.name,
        status: selectedSessionDetail.status,
        inputType: selectedSessionDetail.input_type,
        createdAt: selectedSession?.created_at,
        errorMessage: selectedSessionDetail.error_message,
        audioUrl: selectedSessionDetail.audio_object_key ? getFilePresignedUrl(selectedSessionDetail.audio_object_key) : undefined,
        result: selectedSessionDetail.result,
      }
    : null;

  function closeEmployeeDetail(): void {
    closeSelectedSession();
    window.history.pushState({}, '', '/admin/employees');
    window.dispatchEvent(new PopStateEvent('popstate'));
  }

  return (
    <main className="admin-content-grid">
    {/* Left: Stats + Employee list */}
    <section className="admin-main-panel">
      <div className="admin-kpi-grid">
        <div className="admin-kpi-card card">
          <span className="kpi-icon">👥</span>
          <div className="kpi-info">
            <h3>Tổng số nhân viên</h3>
            <p className="kpi-value">{totalEmployeesCount}</p>
          </div>
        </div>
        <div className="admin-kpi-card card">
          <span className="kpi-icon">🎙️</span>
          <div className="kpi-info">
            <h3>Tổng cuộc phân tích</h3>
            <p className="kpi-value">{totalEmployeeJobs}</p>
          </div>
        </div>
        <div className="admin-kpi-card card">
          <span className="kpi-icon">⭐</span>
          <div className="kpi-info">
            <h3>Điểm chất lượng hệ thống</h3>
            <p className="kpi-value">{systemAvgScore}</p>
          </div>
        </div>
      </div>

      <div className="employees-list-section card">
        <div className="section-header-row">
          <h2>👥 Quản Lý Tiến Độ Nhân Viên</h2>
          <AdminRefreshButton onClick={fetchEmployees} isLoading={isLoading} />
        </div>
        {isLoading ? (
          <div className="loader-container"><div className="loader"></div><p>Đang tải dữ liệu nhân viên...</p></div>
        ) : error ? (
          <div className="auth-error">Lỗi: {error}</div>
        ) : employees.length === 0 ? (
          <p className="no-data">Hệ thống chưa có nhân viên nào đăng ký.</p>
        ) : (
          <div className="employee-table-wrapper">
            <table className="employee-table">
              <thead>
                <tr>
                  <th>Tài khoản</th>
                  <th>Email</th>
                  <th>Số cuộc gọi</th>
                  <th>Điểm TB</th>
                  <th>Sắc thái chính</th>
                  <th>Hành động</th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  // move current user to top if present
                  const ordered = [...employees];
                  try {
                    const idx = ordered.findIndex(e => e.id === currentUserId);
                    if (idx > 0) ordered.unshift(ordered.splice(idx, 1)[0]);
                  } catch (e) {}
                  return ordered.map((emp) => {

                  const pos = emp.sentiment_distribution.positive;
                  const neu = emp.sentiment_distribution.neutral;
                  const neg = emp.sentiment_distribution.negative;
                  let dominantSentiment = 'N/A';
                  const completedJobs = pos + neu + neg;
                  if (completedJobs > 0) {
                    if (pos > neu && pos > neg) {
                      dominantSentiment = 'Positive';
                    } else if (neg > pos && neg > neu) {
                      dominantSentiment = 'Negative';
                    } else {
                      dominantSentiment = 'Neutral';
                    }
                  }
                  return (
                    <tr key={emp.id} className={selectedEmp?.id === emp.id ? 'active-row' : ''} onClick={() => handleSelectEmployee(emp)}>
                      <td>
                        <div className="emp-name-cell">
                          <span className="emp-avatar">{emp.username.substring(0, 2).toUpperCase()}</span>
                          <strong>{emp.username}</strong>{emp.id === currentUserId && <span className="self-badge"> (Bạn)</span>}
                        </div>
                      </td>
                      <td>{emp.email}</td>
                      <td className="text-center">{emp.total_jobs}</td>
                      <td className="text-center font-bold">
                        {emp.average_score !== null ? (
                          <span className={`score-badge ${emp.average_score >= 80 ? 'score-good' : emp.average_score >= 50 ? 'score-normal' : 'score-bad'}`}>
                            {emp.average_score}
                          </span>
                        ) : '-'}
                      </td>
                      <td>
                        <span className={`sentiment-badge ${dominantSentiment.toLowerCase()}`}>
                          {dominantSentiment.toLowerCase() === 'positive' ? 'Tích cực' : 
                           dominantSentiment.toLowerCase() === 'negative' ? 'Tiêu cực' : 
                           dominantSentiment.toLowerCase() === 'neutral' ? 'Trung lập' : 'N/A'}
                        </span>
                      </td>
                      <td>
                        <button className="table-action-btn">📊 Xem chi tiết</button>
                      </td>
                    </tr>
                  );
                });
                })()}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>

    {selectedEmp && (
      <div className="employee-detail-modal-backdrop" role="presentation" onClick={closeEmployeeDetail}>
        <section className="admin-details-panel employee-detail-modal" onClick={(event) => event.stopPropagation()}>
          {isDetailsLoading ? (
            <div className="details-loader card">
              <div className="loader"></div>
              <h3>Đang tải tiến độ...</h3>
              <p>Hệ thống đang tổng hợp dữ liệu riêng biệt của <strong>{selectedEmp.username}</strong></p>
            </div>
          ) : (
            <div className="emp-stats-card card animate-fade-in">
              <PerformanceDashboardPanel
                compact
                profile={{
                  eyebrow: 'Xem chi tiết',
                  title: selectedEmp.username,
                  subtitle: selectedEmp.email,
                  avatarText: selectedEmp.username.substring(0, 2).toUpperCase(),
                }}
                stats={empStats ?? {
                  total_jobs: selectedEmp.total_jobs,
                  average_agent_score: selectedEmp.average_score,
                  average_confidence: 0,
                  sentiment_distribution: selectedEmp.sentiment_distribution,
                  weekly_trends: [],
                }}
                sessions={empSessions}
                onClose={closeEmployeeDetail}
                onSessionClick={(session) => {
                  const detailSession = empSessions.find((item) => item.job_id === session.job_id);
                  if (detailSession) {
                    handleSelectSession(detailSession);
                  }
                }}
              />
            </div>
          )}
          {isSessionDetailLoading && (
            <div className="session-detail-modal-backdrop" role="presentation">
              <div className="details-loader card">
                <div className="loader"></div>
                <h3>Đang tải chi tiết phiên làm việc...</h3>
              </div>
            </div>
          )}
          {selectedSessionViewModel && (
            <SessionDetailModal
              session={selectedSessionViewModel}
              onClose={closeSelectedSession}
            />
          )}
        </section>
      </div>
    )}
  </main>
  );
};
