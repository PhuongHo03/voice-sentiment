import React from 'react';
import { useAdminDashboard } from '../hooks/useAdminDashboard';
import type { Employee, AccountUser } from '../types/admin';

interface AdminDashboardPageProps {
  onBackToPersonal: () => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ onBackToPersonal }) => {
  const {
    logout,
    user,
    activeTab,
    handleSetActiveTab,
    employees,
    selectedEmp,
    empStats,
    empSessions,
    selectedSession,
    setSelectedSession,
    isLoading,
    isDetailsLoading,
    error,
    accounts,
    accountsLoading,
    accountsError,
    toastMessage,
    updatingUserId,
    handleSelectEmployee,
    fetchAccounts,
    handleToggleStatus,
    handleChangeRole,
  } = useAdminDashboard();

  // ── SVG donut helpers ──
  const donutPos = empStats?.sentiment_distribution?.positive ?? selectedEmp?.sentiment_distribution?.positive ?? 0;
  const donutNeu = empStats?.sentiment_distribution?.neutral ?? selectedEmp?.sentiment_distribution?.neutral ?? 0;
  const donutNeg = empStats?.sentiment_distribution?.negative ?? selectedEmp?.sentiment_distribution?.negative ?? 0;
  const donutTotal = donutPos + donutNeu + donutNeg;
  const posPct = donutTotal ? (donutPos / donutTotal) * 100 : 0;
  const neuPct = donutTotal ? (donutNeu / donutTotal) * 100 : 0;
  const negPct = donutTotal ? (donutNeg / donutTotal) * 100 : 0;
  const circ = 2 * Math.PI * 38;
  const negOffset = 0;
  const neuOffset = (donutNeg / donutTotal) * circ;
  const posOffset = ((donutNeg + donutNeu) / donutTotal) * circ;

  // ── KPI ──
  const totalEmployeesCount = employees.length;
  const totalEmployeeJobs = employees.reduce((sum, item) => sum + item.total_jobs, 0);
  const scoredEmployees = employees.filter(e => e.average_score !== null);
  const systemAvgScore = scoredEmployees.length
    ? (scoredEmployees.reduce((sum, item) => sum + (item.average_score || 0), 0) / scoredEmployees.length).toFixed(1)
    : 'Chưa có';

  // ── Account stats ──
  const pendingCount = accounts.filter(a => !a.is_active).length;
  const adminCount = accounts.filter(a => a.role_id === 'admin').length;

  return (
    <div className="admin-layout">
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`admin-toast ${toastMessage.type}`}>
          <span>{toastMessage.type === 'success' ? '✅' : '❌'}</span>
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Top Navigation */}
      <header className="admin-header">
        <div className="admin-logo-sec">
          <span className="live-indicator"></span>
          <h2>VOICE SENTIMENT <span className="admin-pill">Admin Portal</span></h2>
        </div>
        <div className="admin-nav-actions">
          <span className="admin-user-info">Chào, <strong>{user?.username}</strong></span>
          <button onClick={onBackToPersonal} className="nav-btn secondary-btn">
            📂 Chế độ cá nhân
          </button>
          <button onClick={logout} className="nav-btn danger-btn">
            🚪 Đăng xuất
          </button>
        </div>
      </header>

      <nav className="admin-tab-nav">
        <button
          className={`admin-tab-btn ${activeTab === 'performance' ? 'active' : ''}`}
          onClick={() => handleSetActiveTab('performance')}
          id="tab-performance"
        >
          📊 Tiến độ Nhân viên
        </button>
        <button
          className={`admin-tab-btn ${activeTab === 'accounts' ? 'active' : ''}`}
          onClick={() => handleSetActiveTab('accounts')}
          id="tab-accounts"
        >
          🔐 Quản lý Tài khoản
          {pendingCount > 0 && (
            <span className="pending-badge">{pendingCount}</span>
          )}
        </button>
      </nav>

      {/* ════════════════════════════════════════════════════════════
          TAB 1: PERFORMANCE DASHBOARD
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'performance' && (
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
              <h2>👥 Quản Lý Tiến Độ Nhân Viên</h2>
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
                      {employees.map((emp) => {
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
                                <strong>{emp.username}</strong>
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
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>

          {/* Right: Employee details */}
          <section className="admin-details-panel">
            {!selectedEmp ? (
              <div className="no-selection-card card">
                <span className="selection-icon">📊</span>
                <h3>Báo Cáo Hiệu Suất Nhân Viên</h3>
                <p>Chọn một nhân viên bất kỳ từ danh sách bên cạnh để xem biểu đồ hiệu suất, xu hướng làm việc tuần và chi tiết lịch sử cuộc gọi.</p>
              </div>
            ) : isDetailsLoading ? (
              <div className="details-loader card">
                <div className="loader"></div>
                <h3>Đang tải tiến độ...</h3>
                <p>Hệ thống đang tổng hợp dữ liệu riêng biệt của <strong>{selectedEmp.username}</strong></p>
              </div>
            ) : (
              <div className="emp-stats-card card animate-fade-in">
                <div className="emp-details-header">
                  <span className="emp-avatar large">{selectedEmp.username.substring(0, 2).toUpperCase()}</span>
                  <div>
                    <h2>{selectedEmp.username}</h2>
                    <p className="emp-meta-email">📧 {selectedEmp.email}</p>
                  </div>
                </div>

                <div className="emp-performance-summary">
                  {/* Sentiment Donut */}
                  <div className="sentiment-card-mini">
                    <h3>Tỷ Lệ Sắc Thái Cuộc Gọi</h3>
                    {donutTotal > 0 ? (
                      <div className="donut-section-admin">
                        <div className="donut-svg-container-mini">
                          <svg viewBox="0 0 100 100" width="120" height="120">
                            <circle cx="50" cy="50" r="44" stroke="rgba(255,255,255,0.03)" strokeWidth="8" fill="none" />
                            {donutNeg > 0 && (<circle cx="50" cy="50" r="38" stroke="var(--color-rose)" strokeWidth="8" fill="none" strokeDasharray={`${(donutNeg / donutTotal) * circ} ${circ}`} strokeDashoffset={-negOffset} transform="rotate(-90 50 50)" className="donut-chart-circle" />)}
                            {donutNeu > 0 && (<circle cx="50" cy="50" r="38" stroke="var(--color-blue)" strokeWidth="8" fill="none" strokeDasharray={`${(donutNeu / donutTotal) * circ} ${circ}`} strokeDashoffset={-neuOffset} transform="rotate(-90 50 50)" className="donut-chart-circle" />)}
                            {donutPos > 0 && (<circle cx="50" cy="50" r="38" stroke="var(--color-teal)" strokeWidth="8" fill="none" strokeDasharray={`${(donutPos / donutTotal) * circ} ${circ}`} strokeDashoffset={-posOffset} transform="rotate(-90 50 50)" className="donut-chart-circle" />)}
                            <text x="50" y="53" textAnchor="middle" fontSize="13" fontWeight="800" fill="#fff">{donutTotal}</text>
                          </svg>
                        </div>
                        <div className="donut-legend-mini">
                          <div className="legend-item-mini"><span className="dot teal"></span> Tích cực: {Math.round(posPct)}%</div>
                          <div className="legend-item-mini"><span className="dot neutral"></span> Trung lập: {Math.round(neuPct)}%</div>
                          <div className="legend-item-mini"><span className="dot rose"></span> Tiêu cực: {Math.round(negPct)}%</div>
                        </div>
                      </div>
                    ) : (<p className="no-data-mini">Chưa có sắc thái cuộc gọi</p>)}
                  </div>

                  {/* Score Gauge */}
                  <div className="agent-score-mini">
                    <h3>Điểm Chất Lượng AI</h3>
                    {empStats?.average_agent_score !== undefined && empStats?.average_agent_score !== null ? (
                      <div className="circular-score-wrapper">
                        <div className={`circular-score-badge ${empStats.average_agent_score >= 80 ? 'good' : empStats.average_agent_score >= 50 ? 'warn' : 'bad'}`}>
                          <span className="score-num">{empStats.average_agent_score}</span>
                          <span className="score-label">/100đ</span>
                        </div>
                        <p className="score-hint">
                          {empStats.average_agent_score >= 80 ? 'Đạt chuẩn xuất sắc' : empStats.average_agent_score >= 50 ? 'Trung bình khá' : 'Cần cải thiện'}
                        </p>
                      </div>
                    ) : (<p className="no-data-mini">Chưa có điểm số</p>)}
                  </div>
                </div>

                {/* Weekly Trends Bar Chart */}
                {empStats && empStats.weekly_trends && empStats.weekly_trends.length > 0 && (
                  <div className="weekly-trends-card card-inner">
                    <h3>Biểu đồ năng suất (7 ngày gần nhất)</h3>
                    <div className="bar-chart-container">
                      <svg viewBox="0 0 350 120" width="100%" height="100px">
                        <line x1="20" y1="100" x2="340" y2="100" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
                        <line x1="20" y1="50" x2="340" y2="50" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                        <line x1="20" y1="10" x2="340" y2="10" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                        {(() => {
                          const maxCount = Math.max(...empStats.weekly_trends.map(t => t.count), 4);
                          return empStats.weekly_trends.map((t, idx) => {
                            const barWidth = 24, barGap = 16;
                            const x = 30 + idx * (barWidth + barGap);
                            const barHeight = (t.count / maxCount) * 80;
                            const y = 100 - barHeight;
                            const shortDate = t.date.substring(5).replace('-', '/');
                            return (
                              <g key={t.date}>
                                <rect x={x - 2} y={10} width={barWidth + 4} height={90} fill="rgba(255,255,255,0.01)" rx="4" />
                                <rect x={x} y={y} width={barWidth} height={barHeight} fill="url(#glowing-violet-gradient)" rx="4" className="chart-bar" />
                                {t.count > 0 && (<text x={x + barWidth / 2} y={y - 5} textAnchor="middle" fontSize="8" fontWeight="700" fill="#c084fc">{t.count}</text>)}
                                <text x={x + barWidth / 2} y={112} textAnchor="middle" fontSize="7" fontWeight="600" fill="var(--text-secondary)">{shortDate}</text>
                              </g>
                            );
                          });
                        })()}
                        <defs>
                          <linearGradient id="glowing-violet-gradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--color-primary)" />
                            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.4" />
                          </linearGradient>
                        </defs>
                      </svg>
                    </div>
                  </div>
                )}

                {/* Sessions List */}
                <div className="emp-sessions-list-sec">
                  <h3>📜 Lịch Sử Làm Việc</h3>
                  {empSessions.length === 0 ? (
                    <p className="no-data-mini">Nhân viên này chưa thực hiện phiên phân tích nào.</p>
                  ) : (
                    <div className="emp-session-cards-wrapper">
                      {empSessions.map((sessionItem) => (
                        <div key={sessionItem.job_id} className={`emp-session-mini-card ${selectedSession?.job_id === sessionItem.job_id ? 'active' : ''}`} onClick={() => setSelectedSession(sessionItem)}>
                          <div className="session-mini-head">
                            <span className={`mini-badge ${sessionItem.input_type}`}>{sessionItem.input_type === 'audio' ? '🎙️ Audio' : '📝 Text'}</span>
                            <span className="session-mini-date">{new Date(sessionItem.created_at).toLocaleDateString('vi-VN', { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                          <h4 className="session-mini-name">{sessionItem.name || 'Không có tiêu đề'}</h4>
                          <div className="session-mini-footer">
                            {(sessionItem.agent_score !== null && sessionItem.agent_score !== undefined) && (
                              <span className="mini-score" style={{ color: sessionItem.agent_score >= 80 ? 'var(--color-teal)' : sessionItem.agent_score >= 50 ? 'var(--color-blue)' : 'var(--color-rose)', fontWeight: 'bold' }}>
                                ⭐ {sessionItem.agent_score}/100đ
                              </span>
                            )}
                            {sessionItem.sentiment && (<span className={`sentiment-badge-mini ${sessionItem.sentiment.toLowerCase()}`}>{sessionItem.sentiment.toLowerCase() === 'positive' ? 'Tích cực' : sessionItem.sentiment.toLowerCase() === 'negative' ? 'Tiêu cực' : 'Trung lập'}</span>)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Session Detail */}
                {selectedSession && (
                  <div className="selected-session-overlay animate-fade-in card">
                    <div className="overlay-header">
                      <h3>🔍 Chi Tiết Phiên Làm Việc</h3>
                      <button onClick={() => setSelectedSession(null)} className="close-overlay-btn">&times;</button>
                    </div>
                    <div className="overlay-content">
                      <h4>{selectedSession.name}</h4>
                      <p className="overlay-meta">📅 {new Date(selectedSession.created_at).toLocaleString('vi-VN')} | 📊 Loại: {selectedSession.input_type === 'audio' ? 'Âm thanh' : 'Văn bản'}</p>
                      <div className="overlay-score-row">
                        <div className="stat-pill-mini">
                          <span className="pill-lbl">Cảm xúc:</span>
                          <span className={`sentiment-badge ${selectedSession.sentiment?.toLowerCase() || ''}`}>{selectedSession.sentiment?.toLowerCase() === 'positive' ? 'Tích cực' : selectedSession.sentiment?.toLowerCase() === 'negative' ? 'Tiêu cực' : 'Trung lập'}</span>
                        </div>
                        {(selectedSession.agent_score !== null && selectedSession.agent_score !== undefined) && (
                          <div className="stat-pill-mini">
                            <span className="pill-lbl">Kỹ năng CSKH:</span>
                            <strong style={{ color: selectedSession.agent_score >= 80 ? 'var(--color-teal)' : selectedSession.agent_score >= 50 ? 'var(--color-blue)' : 'var(--color-rose)' }}>
                              {selectedSession.agent_score}/100đ
                            </strong>
                          </div>
                        )}
                      </div>
                      {selectedSession.summary && selectedSession.summary.length > 0 && (
                        <div className="overlay-block">
                          ... Tóm tắt cuộc gọi ...
                          <ul className="bullet-list-mini">{selectedSession.summary.map((s, i) => <li key={i}>{s}</li>)}</ul>
                        </div>
                      )}
                      {selectedSession.sentiment_reason && (
                        <div className="overlay-block">
                          <h5>💡 Phân tích nguyên nhân sắc thái:</h5>
                          <p className="paragraph-mini">{selectedSession.sentiment_reason}</p>
                        </div>
                      )}
                      {selectedSession.transcript && selectedSession.transcript.length > 0 && (
                        <div className="overlay-block">
                          <h5>💬 Nội dung hội thoại chi tiết:</h5>
                          <div className="dialogue-box-mini">
                            {selectedSession.transcript.map((chat: any, idx: number) => {
                              const isAgent = chat.speaker?.toLowerCase().includes('agent') || chat.speaker?.toLowerCase().includes('nhân viên');
                              return (
                                <div key={idx} className={`dialogue-item ${isAgent ? 'agent-row' : 'customer-row'}`}>
                                  <span className="speaker-tag">{chat.speaker || (isAgent ? 'Nhân viên' : 'Khách hàng')}:</span>
                                  <p className="dialogue-text">{chat.text}</p>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      {selectedSession.agent_advice && selectedSession.agent_advice.length > 0 && (
                        <div className="overlay-block border-top-violet">
                          <h5>💡 Lời khuyên của AI cho nhân viên:</h5>
                          <ul className="bullet-list-mini advice-list-mini">{selectedSession.agent_advice.map((adv, idx) => <li key={idx}>💡 {adv}</li>)}</ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        </main>
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB 2: ACCOUNT MANAGEMENT
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'accounts' && (
        <main className="account-mgmt-layout">
          {/* Stats row */}
          <div className="acct-kpi-grid">
            <div className="acct-kpi-card card">
              <span className="kpi-icon">👤</span>
              <div className="kpi-info">
                <h3>Tổng tài khoản</h3>
                <p className="kpi-value">{accounts.length}</p>
              </div>
            </div>
            <div className="acct-kpi-card card">
              <span className="kpi-icon kpi-warn">⏳</span>
              <div className="kpi-info">
                <h3>Chờ kích hoạt</h3>
                <p className="kpi-value kpi-warn">{pendingCount}</p>
              </div>
            </div>
            <div className="acct-kpi-card card">
              <span className="kpi-icon">🛡️</span>
              <div className="kpi-info">
                <h3>Quản trị viên</h3>
                <p className="kpi-value">{adminCount}</p>
              </div>
            </div>
            <div className="acct-kpi-card card">
              <span className="kpi-icon">✅</span>
              <div className="kpi-info">
                <h3>Đang hoạt động</h3>
                <p className="kpi-value kpi-good">{accounts.filter(a => a.is_active).length}</p>
              </div>
            </div>
          </div>

          {/* Accounts table */}
          <div className="account-table-section card">
            <div className="section-header-row">
              <h2>🔐 Quản Lý Tài Khoản Hệ Thống</h2>
              <button className="refresh-btn" onClick={fetchAccounts} title="Làm mới danh sách">
                🔄 Làm mới
              </button>
            </div>

            {accountsLoading ? (
              <div className="loader-container"><div className="loader"></div><p>Đang tải danh sách tài khoản...</p></div>
            ) : accountsError ? (
              <div className="auth-error">Lỗi: {accountsError}</div>
            ) : accounts.length === 0 ? (
              <p className="no-data">Chưa có tài khoản nào trong hệ thống.</p>
            ) : (
              <div className="account-table-wrapper">
                <table className="account-table">
                  <thead>
                    <tr>
                      <th>Tài khoản</th>
                      <th>Email</th>
                      <th>Vai trò</th>
                      <th>Ngày tạo</th>
                      <th className="text-center">Trạng thái</th>
                      <th className="text-center">Kích hoạt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((acc) => {
                      const isSelf = acc.id === user?.id;
                      const isUpdating = updatingUserId === acc.id;
                      return (
                        <tr key={acc.id} className={`acct-row ${!acc.is_active ? 'inactive-row' : ''} ${isSelf ? 'self-row' : ''}`}>
                          <td>
                            <div className="emp-name-cell">
                              <span className={`emp-avatar ${acc.role_id === 'admin' ? 'admin-avatar' : ''}`}>
                                {acc.username.substring(0, 2).toUpperCase()}
                              </span>
                              <div>
                                <strong>{acc.username}</strong>
                                {isSelf && <span className="self-badge"> (Bạn)</span>}
                              </div>
                            </div>
                          </td>
                          <td className="email-cell">{acc.email}</td>
                          <td>
                            {isSelf ? (
                              <span className={`role-pill ${acc.role_id}`}>{acc.role_id === 'admin' ? '🛡️ Admin' : '👤 Nhân viên'}</span>
                            ) : (
                              <select
                                className={`role-select ${acc.role_id}`}
                                value={acc.role_id}
                                disabled={isUpdating}
                                onChange={(e) => handleChangeRole(acc, e.target.value)}
                              >
                                <option value="employee">👤 Nhân viên</option>
                                <option value="admin">🛡️ Admin</option>
                              </select>
                            )}
                          </td>
                          <td className="date-cell">
                            {new Date(acc.created_at).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                          </td>
                          <td className="text-center">
                            <span className={`status-pill ${acc.is_active ? 'active' : 'inactive'}`}>
                              {acc.is_active ? '✅ Hoạt động' : '⏳ Chờ duyệt'}
                            </span>
                          </td>
                          <td className="text-center">
                            {isSelf ? (
                              <span className="no-action-hint">—</span>
                            ) : (
                              <button
                                className={`toggle-status-btn ${acc.is_active ? 'deactivate' : 'activate'}`}
                                onClick={() => handleToggleStatus(acc)}
                                disabled={isUpdating}
                                title={acc.is_active ? 'Vô hiệu hóa tài khoản' : 'Kích hoạt tài khoản'}
                              >
                                {isUpdating ? (
                                  <span className="btn-spinner"></span>
                                ) : acc.is_active ? (
                                  '🔒 Vô hiệu hóa'
                                ) : (
                                  '🔓 Kích hoạt'
                                )}
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </main>
      )}
    </div>
  );
};

export default AdminDashboardPage;
