import { useState } from 'react';
import { AudioInputPanel } from '../components/audio/AudioInputPanel';
import { SentimentBadge } from '../components/sentiment/SentimentBadge';
import { SummaryCard } from '../components/summary/SummaryCard';
import { TranscriptLog } from '../components/transcript/TranscriptLog';
import { useAuth } from '../../auth/states/AuthContext';
import { useDashboardAnalysis } from '../hooks/useAnalysis';
import { getFilePresignedUrl } from '../api/analysisApi';

export function DashboardPage({ isAdmin = false, onGoToAdmin }: { isAdmin?: boolean; onGoToAdmin?: () => void }) {
  const { logout, user } = useAuth();
  const {
    sessions,
    activeSessionId,
    setActiveSessionIdPersisted,
    activeSessionDetail,
    searchQuery,
    setSearchQuery,
    loading,
    error,
    setError,
    sessionsLoading,
    activeView,
    setActiveViewPersisted,
    stats,
    statsLoading,
    editingSessionId,
    setEditingSessionId,
    editingName,
    setEditingName,
    isSidebarOpen,
    setIsSidebarOpen,
    filteredSessions,
    handleCreateNewSession,
    handleAudioSubmit,
    handleAudioFromKey,
    handleUploadFileOnly,
    handleTextSubmit,
    handleSaveRename,
    handleDeleteSession,
    formatRelativeTime,
    formatFileSize,
    getDominantSentiment,
    loadStats,
    // MinIO file management
    userFiles,
    filesLoading,
    filesError,
    loadUserFiles,
    handleDeleteUserFile,
  } = useDashboardAnalysis(isAdmin);

  // Audio preview state for the Files view
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const token = localStorage.getItem('voice_sentiment_token') ?? '';
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';
  const sessionAudioUrl = activeSessionDetail?.audio_object_key
    ? `${apiBaseUrl}/api/files/stream?object_key=${encodeURIComponent(activeSessionDetail.audio_object_key)}&token=${encodeURIComponent(token)}`
    : null;

  async function handlePreviewFile(objectKey: string) {
    if (previewKey === objectKey) {
      setPreviewUrl(null);
      setPreviewKey(null);
      return;
    }
    setPreviewLoading(true);
    try {
      const url = await getFilePresignedUrl(objectKey);
      setPreviewUrl(url);
      setPreviewKey(objectKey);
    } catch (e) {
      alert('Không thể tải link phát lại: ' + (e instanceof Error ? e.message : 'Lỗi'));
    } finally {
      setPreviewLoading(false);
    }
  }

  // Pre-calculate SVG Donut Chart lengths
  const donutPos = stats?.sentiment_distribution?.positive || 0;
  const donutNeu = stats?.sentiment_distribution?.neutral || 0;
  const donutNeg = stats?.sentiment_distribution?.negative || 0;
  const donutTotal = donutPos + donutNeu + donutNeg;
  
  const posPct = donutTotal ? (donutPos / donutTotal) * 100 : 0;
  const neuPct = donutTotal ? (donutNeu / donutTotal) * 100 : 0;
  const negPct = donutTotal ? (donutNeg / donutTotal) * 100 : 0;
  
  const circ = 251.3; // 2 * PI * r (r=40)
  const posLen = (posPct / 100) * circ;
  const neuLen = (neuPct / 100) * circ;
  const negLen = (negPct / 100) * circ;

  const posStart = 0;
  const neuStart = posLen;
  const negStart = posLen + neuLen;

  const posOffset = -posStart;
  const neuOffset = -neuStart;
  const negOffset = -negStart;

  // Pre-calculate SVG Bar Chart scaling
  const trendsList = stats?.weekly_trends || [];
  const maxTrendCount = Math.max(...trendsList.map((t: any) => t.count), 1);

  return (
    <div className="app-layout-shell">
      {/* SIDEBAR FOR SESSION HISTORY */}
      <aside className={`session-sidebar ${!isSidebarOpen ? 'collapsed' : ''}`}>
        {isSidebarOpen ? (
          <>
            {/* Full Expanded Sidebar */}
            <div className="sidebar-header">
              <div className="sidebar-top-row">
                <div className="brand-section">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--color-primary)' }}><path d="M12 20v-6M9 20v-10M6 20v-4M12 20h8M18 20V4M21 20h2M3 20h3M15 20v-8M15 8V4M12 4h6"></path></svg>
                  <span>Console History</span>
                </div>
                <button
                  className="sidebar-toggle-btn"
                  onClick={() => setIsSidebarOpen(false)}
                  title="Thu gọn Lịch sử"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="18" height="18" x="3" y="3" rx="2"/>
                    <path d="M9 3v18"/>
                  </svg>
                </button>
              </div>

              {/* Sidebar navigations to switch between views */}
              <div className="sidebar-nav-actions" style={{ marginTop: '12px' }}>
                <div 
                  className={`sidebar-action-item ${activeView === 'session' ? 'active' : ''}`}
                  onClick={() => setActiveViewPersisted('session')}
                  title="Hệ thống Console"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5v14M22 8v8M7 8v8M2 10v4"/></svg>
                  <span>Phân tích cuộc gọi</span>
                </div>
                <div 
                  className={`sidebar-action-item ${activeView === 'dashboard' ? 'active' : ''}`}
                  onClick={() => setActiveViewPersisted('dashboard')}
                  title="Dashboard Thống kê"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                  <span>Dashboard Thống kê</span>
                </div>
                <div 
                  className={`sidebar-action-item ${activeView === 'files' ? 'active' : ''}`}
                  onClick={() => { setActiveViewPersisted('files'); loadUserFiles(); }}
                  title="File của tôi"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                  <span>File của tôi</span>
                  {userFiles.length > 0 && (
                    <span style={{ marginLeft: 'auto', background: 'rgba(139,92,246,0.2)', color: 'var(--color-primary)', borderRadius: '99px', fontSize: '0.7rem', padding: '1px 6px', fontWeight: 700 }}>{userFiles.length}</span>
                  )}
                </div>
                {isAdmin && onGoToAdmin && (
                  <div 
                    className="sidebar-action-item admin"
                    onClick={onGoToAdmin}
                    title="Hệ thống Quản trị Admin"
                    style={{ border: '1px solid rgba(139, 92, 246, 0.3)', background: 'rgba(139, 92, 246, 0.05)', marginTop: '4px' }}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--color-primary)' }}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    <span style={{ fontWeight: 'bold', color: 'var(--color-primary)' }}>Admin Portal</span>
                  </div>
                )}
              </div>

              <button className="new-session-button-wide" onClick={handleCreateNewSession} style={{ marginTop: '8px' }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4Z" />
                </svg>
                Tạo session mới
              </button>
            </div>

            <div className="search-container">
              <div className="search-input-wrapper">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                <input
                  type="text"
                  className="search-input"
                  placeholder="Tìm kiếm session..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="session-list">
              {sessionsLoading ? (
                <div className="sidebar-empty">Đang tải lịch sử...</div>
              ) : filteredSessions.length === 0 ? (
                <div className="sidebar-empty">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
                  Không tìm thấy session nào
                </div>
              ) : (
                filteredSessions.map((s) => {
                  const isActive = activeSessionId === s.job_id && activeView === 'session';
                  const isEditing = editingSessionId === s.job_id;

                  return (
                    <div key={s.job_id} className="session-card-container">
                      {isEditing ? (
                        <div className="session-card active">
                          <input
                            type="text"
                            className="inline-edit-input"
                            value={editingName}
                            onChange={(e) => setEditingName(e.target.value)}
                            autoFocus
                          />
                          <div className="inline-edit-actions">
                            <button
                              className="session-action-btn"
                              onClick={() => handleSaveRename(s.job_id)}
                              title="Lưu"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            </button>
                            <button
                              className="session-action-btn"
                              onClick={() => setEditingSessionId(null)}
                              title="Hủy"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div
                          className={`session-card ${isActive ? 'active' : ''}`}
                          onClick={() => {
                            setActiveViewPersisted('session');
                            setActiveSessionIdPersisted(s.job_id);
                          }}
                        >
                          <div className="session-card-header">
                            <div className="session-card-title-section">
                              <span className="session-card-icon">
                                {s.input_type === 'text' ? '📝' : '🎵'}
                              </span>
                              <span className="session-card-title" title={s.name || 'Không tên'}>
                                {s.name || 'Không tên'}
                              </span>
                            </div>
                            <div className="session-card-actions">
                              <button
                                className="session-action-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setEditingSessionId(s.job_id);
                                  setEditingName(s.name || '');
                                }}
                                title="Đổi tên"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                              </button>
                              <button
                                className="session-action-btn delete"
                                onClick={(e) => handleDeleteSession(s.job_id, e)}
                                title="Xóa"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                              </button>
                            </div>
                          </div>
                          <div className="session-card-meta">
                            <span>{formatRelativeTime(s.created_at)}</span>
                            {s.status === 'completed' && s.sentiment && (
                              <span className={`session-card-sentiment-badge ${s.sentiment.toLowerCase()}`}>
                                {s.sentiment.toLowerCase() === 'positive' ? 'Tích cực' : 
                                 s.sentiment.toLowerCase() === 'negative' ? 'Tiêu cực' : 'Trung lập'}
                              </span>
                            )}
                            {(s.status === 'pending' || s.status === 'processing') && (
                              <span className={`session-card-sentiment-badge ${s.status}`}>
                                {s.status === 'pending' ? 'Chờ...' : 'Đang xử lý...'}
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
            {/* User Profile & Logout section in Sidebar */}
            <div className="sidebar-profile-footer" style={{ 
              padding: '16px', 
              borderTop: '1px solid var(--glass-border)', 
              marginTop: 'auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              background: 'rgba(0, 0, 0, 0.2)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                <span className="emp-avatar" style={{ width: '28px', height: '28px', fontSize: '12px', flexShrink: 0 }}>
                  {user?.username?.substring(0, 2).toUpperCase()}
                </span>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user?.username}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                    {user?.role_id === 'admin' ? 'Quản trị' : 'Nhân viên'}
                  </div>
                </div>
              </div>
              <button 
                onClick={logout} 
                className="logout-icon-btn" 
                title="Đăng xuất"
                style={{ 
                  width: '32px', 
                  height: '32px', 
                  padding: 0, 
                  marginTop: 0, 
                  borderRadius: '8px',
                  background: 'rgba(244, 63, 94, 0.1)',
                  color: 'var(--color-rose)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid rgba(244, 63, 94, 0.2)',
                  cursor: 'pointer'
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
              </button>
            </div>
          </>
        ) : (
          /* Slim Collapsed Sidebar (ChatGPT Style) */
          <div className="collapsed-sidebar-items">
            <button
              className="sidebar-toggle-btn"
              onClick={() => setIsSidebarOpen(true)}
              title="Mở rộng Lịch sử"
              style={{ margin: '8px 0' }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect width="18" height="18" x="3" y="3" rx="2"/>
                <path d="M9 3v18"/>
              </svg>
            </button>

            {/* Icons navigation for collapsed sidebar */}
            <div className="sidebar-nav-actions" style={{ width: '100%', alignItems: 'center' }}>
              <div 
                className={`sidebar-action-item ${activeView === 'session' ? 'active' : ''}`}
                onClick={() => setActiveViewPersisted('session')}
                title="Phân tích cuộc gọi"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5v14M22 8v8M7 8v8M2 10v4"/></svg>
              </div>
              <div 
                className={`sidebar-action-item ${activeView === 'dashboard' ? 'active' : ''}`}
                onClick={() => setActiveViewPersisted('dashboard')}
                title="Dashboard Thống kê"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
              </div>
              <div 
                className={`sidebar-action-item ${activeView === 'files' ? 'active' : ''}`}
                onClick={() => { setActiveViewPersisted('files'); loadUserFiles(); }}
                title="File của tôi"
                style={{ position: 'relative' }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                {userFiles.length > 0 && (
                  <span style={{ position: 'absolute', top: '2px', right: '2px', width: '8px', height: '8px', background: 'var(--color-primary)', borderRadius: '50%' }} />
                )}
              </div>
              {isAdmin && onGoToAdmin && (
                <div 
                  className="sidebar-action-item admin"
                  onClick={onGoToAdmin}
                  title="Admin Portal"
                  style={{ border: '1px solid rgba(139, 92, 246, 0.3)', background: 'rgba(139, 92, 246, 0.05)', marginTop: '4px' }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--color-primary)' }}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                </div>
              )}
            </div>

            <button
              className="new-session-button-slim"
              onClick={() => {
                setActiveViewPersisted('session');
                handleCreateNewSession();
              }}
              title="Tạo session mới"
              style={{ margin: '8px 0' }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4Z" />
              </svg>
            </button>

            {/* Collapsed logout button */}
            <div style={{ marginTop: 'auto', padding: '8px 0', width: '100%', display: 'flex', justifyContent: 'center' }}>
              <button 
                onClick={logout} 
                title="Đăng xuất"
                style={{ 
                  width: '32px', 
                  height: '32px', 
                  padding: 0, 
                  marginTop: 0, 
                  borderRadius: '8px',
                  background: 'rgba(244, 63, 94, 0.1)',
                  color: 'var(--color-rose)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid rgba(244, 63, 94, 0.2)',
                  cursor: 'pointer'
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
              </button>
            </div>

            {/* List of session circles with custom thin scrollbar */}
            <div className="collapsed-sessions-container">
              {sessions.map(s => {
                const isActive = activeSessionId === s.job_id && activeView === 'session';
                return (
                  <div
                    key={s.job_id}
                    className={`collapsed-session-circle ${isActive ? 'active' : ''}`}
                    onClick={() => {
                      setActiveViewPersisted('session');
                      setActiveSessionIdPersisted(s.job_id);
                    }}
                    title={s.name || 'Không tên'}
                  >
                    <span style={{ fontSize: '1rem' }}>{s.input_type === 'text' ? '📝' : '🎵'}</span>
                    {s.status === 'completed' && s.sentiment && (
                      <span className={`sentiment-dot-indicator ${s.sentiment.toLowerCase()}`} />
                    )}
                    {(s.status === 'pending' || s.status === 'processing') && (
                      <span className={`sentiment-dot-indicator ${s.status}`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </aside>

      {/* MAIN MAIN CONTENT PANEL */}
      <div className="app-main-content">
        <div className="scrollable-main-container">
          <div className="app-container-full">
            <header className="main-header">
              <div className="logo-section">
                <h1>Voice Sentiment Console</h1>
              </div>
              <p className="subtitle">
                Hệ thống phân tích giọng nói, tóm tắt và đánh giá sắc thái cảm xúc cuộc gọi tiếng Việt
              </p>
            </header>

            {activeView === 'dashboard' ? (
              /* DASHBOARD VIEW PANEL */
              <div className="dashboard-view-container">
                {statsLoading && !stats ? (
                  <div className="session-status-progress">
                    <div className="session-progress-spinner"></div>
                    <div className="session-progress-text">Đang tải báo cáo thống kê tổng hợp...</div>
                  </div>
                ) : (
                  <>
                    {/* KPI Cards Grid */}
                    <div className="stats-grid">
                      <div className="metric-card primary">
                        <span className="metric-label">Tổng số cuộc phân tích</span>
                        <span className="metric-value">{stats?.total_jobs ?? 0}</span>
                        <div className="metric-subtext">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                          Phiên hoàn thành trong hệ thống
                        </div>
                      </div>
                      <div className="metric-card success">
                        <span className="metric-label">Độ tin cậy trung bình</span>
                        <span className="metric-value">
                          {stats?.total_jobs ? `${Math.round((stats?.average_confidence ?? 0) * 100)}%` : '0%'}
                        </span>
                        <div className="metric-subtext">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                          Mức độ tự tin trung bình của LLM
                        </div>
                      </div>
                      <div className="metric-card warning">
                        <span className="metric-label">Điểm nhân viên trung bình</span>
                        <span className="metric-value">
                          {stats?.total_jobs ? `${stats?.average_agent_score ?? 0}` : '0'}<span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/100</span>
                        </span>
                        <div className="metric-subtext">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>
                          Đánh giá chất lượng hỗ trợ
                        </div>
                      </div>
                      <div className="metric-card info">
                        <span className="metric-label">Sắc thái chủ đạo</span>
                        <span className="metric-value">
                          {getDominantSentiment(stats?.sentiment_distribution)}
                        </span>
                        <div className="metric-subtext">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>
                          Sắc thái có tần suất cao nhất
                        </div>
                      </div>
                    </div>

                    {/* Interactive SVG Charts Grid */}
                    <div className="charts-grid">
                      {/* Donut Chart Card */}
                      <div className="chart-card">
                        <h3>
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2v10l8.5 6"></path></svg>
                          Tỉ lệ Phân bố Sắc thái (Sentiment Ratio)
                        </h3>
                        <div className="chart-card-content">
                          {donutTotal > 0 ? (
                            <div className="donut-svg-container">
                              <svg width="160" height="160" viewBox="0 0 100 100">
                                {/* Base background ring */}
                                <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="12" />
                                
                                {/* Negative arc segment */}
                                {donutNeg > 0 && (
                                  <circle
                                    cx="50"
                                    cy="50"
                                    r="40"
                                    fill="none"
                                    stroke="var(--color-rose)"
                                    strokeWidth="12"
                                    strokeDasharray={`${negLen} ${circ}`}
                                    strokeDashoffset={negOffset}
                                    transform="rotate(-90 50 50)"
                                    className="donut-chart-circle"
                                    style={{ '--glow-color': 'rgba(244,63,94,0.4)' } as any}
                                  />
                                )}
                                
                                {/* Neutral arc segment */}
                                {donutNeu > 0 && (
                                  <circle
                                    cx="50"
                                    cy="50"
                                    r="40"
                                    fill="none"
                                    stroke="var(--color-blue)"
                                    strokeWidth="12"
                                    strokeDasharray={`${neuLen} ${circ}`}
                                    strokeDashoffset={neuOffset}
                                    transform="rotate(-90 50 50)"
                                    className="donut-chart-circle"
                                    style={{ '--glow-color': 'rgba(59,130,246,0.4)' } as any}
                                  />
                                )}
                                
                                {/* Positive arc segment */}
                                {donutPos > 0 && (
                                  <circle
                                    cx="50"
                                    cy="50"
                                    r="40"
                                    fill="none"
                                    stroke="var(--color-teal)"
                                    strokeWidth="12"
                                    strokeDasharray={`${posLen} ${circ}`}
                                    strokeDashoffset={posOffset}
                                    transform="rotate(-90 50 50)"
                                    className="donut-chart-circle"
                                    style={{ '--glow-color': 'rgba(16,185,129,0.4)' } as any}
                                  />
                                )}

                                {/* Central text labels */}
                                <text className="donut-center-text" x="50" y="47" fontSize="13" fontWeight="800">
                                  {donutTotal}
                                </text>
                                <text className="donut-center-text" x="50" y="60" fontSize="7" fontWeight="600" fill="var(--text-secondary)">
                                  SESSIONS
                                </text>
                              </svg>
                              
                              <div className="donut-legend">
                                <div className="donut-legend-item">
                                  <span className="legend-color-box positive" />
                                  <span>Tích cực: <strong>{donutPos}</strong> ({Math.round(posPct)}%)</span>
                                </div>
                                <div className="donut-legend-item">
                                  <span className="legend-color-box neutral" />
                                  <span>Trung lập: <strong>{donutNeu}</strong> ({Math.round(neuPct)}%)</span>
                                </div>
                                <div className="donut-legend-item">
                                  <span className="legend-color-box negative" />
                                  <span>Tiêu cực: <strong>{donutNeg}</strong> ({Math.round(negPct)}%)</span>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Chưa có dữ liệu phân tích</span>
                          )}
                        </div>
                      </div>

                      {/* Weekly Trend Bar Chart Card */}
                      <div className="chart-card">
                        <h3>
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                          Xu hướng cuộc gọi trong tuần (Weekly Trends)
                        </h3>
                        <div className="chart-card-content" style={{ display: 'block' }}>
                          {trendsList.length > 0 ? (
                            <div className="bar-chart-container">
                              <svg className="bar-svg" viewBox="0 0 450 200">
                                <defs>
                                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#c084fc" stopOpacity="0.8" />
                                    <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.3" />
                                  </linearGradient>
                                </defs>
                                
                                {/* Grid lines */}
                                <line x1="30" y1="20" x2="430" y2="20" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                                <line x1="30" y1="70" x2="430" y2="70" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                                <line x1="30" y1="120" x2="430" y2="120" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                                <line x1="30" y1="170" x2="430" y2="170" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />

                                {/* Render bars */}
                                {trendsList.map((item: any, idx: number) => {
                                  const x = 50 + idx * 55;
                                  const barMaxHeight = 135;
                                  const barHeight = (item.count / maxTrendCount) * barMaxHeight;
                                  const y = 170 - barHeight;
                                  
                                  // Short date formatting (e.g. 26/05)
                                  let shortDate = item.date;
                                  try {
                                    const parts = item.date.split('-');
                                    shortDate = `${parts[2]}/${parts[1]}`;
                                  } catch (e) {}

                                  return (
                                    <g key={item.date}>
                                      {/* Interactive Bar */}
                                      <rect
                                        className="chart-bar-rect"
                                        x={x}
                                        y={y}
                                        width="32"
                                        height={barHeight}
                                        rx="4"
                                      />
                                      {/* Bar Count Top Label */}
                                      <text
                                        x={x + 16}
                                        y={y - 6}
                                        textAnchor="middle"
                                        fill="#fff"
                                        fontSize="9"
                                        fontWeight="700"
                                        opacity={item.count > 0 ? 1 : 0.2}
                                      >
                                        {item.count}
                                      </text>
                                      {/* X Axis Date Label */}
                                      <text
                                        x={x + 16}
                                        y="188"
                                        textAnchor="middle"
                                        fill="var(--text-secondary)"
                                        fontSize="9"
                                        fontWeight="500"
                                      >
                                        {shortDate}
                                      </text>
                                    </g>
                                  );
                                })}
                              </svg>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                              Không có dữ liệu xu hướng
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : activeView === 'files' ? (
              /* FILES VIEW PANEL */
              <div className="dashboard-view-container">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: '1.3rem', fontWeight: 700 }}>📁 File của tôi</h2>
                    <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Các file âm thanh đã tải lên hoặc ghi âm, lưu trữ trên MinIO</p>
                  </div>
                  <button
                    onClick={loadUserFiles}
                    disabled={filesLoading}
                    style={{ margin: 0, padding: '8px 16px', fontSize: '0.85rem', background: 'rgba(255,255,255,0.06)', border: '1px solid var(--glass-border)', borderRadius: '10px', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
                    {filesLoading ? 'Đang tải...' : 'Làm mới'}
                  </button>
                </div>

                {filesError && (
                  <div className="error-panel" style={{ marginBottom: '16px' }}>{filesError}</div>
                )}

                {filesLoading && userFiles.length === 0 ? (
                  <div className="session-status-progress">
                    <div className="session-progress-spinner"></div>
                    <div className="session-progress-text">Đang tải danh sách file từ MinIO...</div>
                  </div>
                ) : userFiles.length === 0 ? (
                  <div className="card" style={{ padding: '60px 40px', textAlign: 'center' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📂</div>
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px' }}>Chưa có file nào</h3>
                    <p style={{ color: 'var(--text-secondary)', maxWidth: '360px', margin: '0 auto' }}>Tải lên file âm thanh hoặc ghi âm trực tiếp để file xuất hiện ở đây.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {userFiles.map((file) => (
                      <div key={file.object_key} className="card" style={{ padding: '16px 20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                          {/* File icon */}
                          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                          </div>

                          {/* File info */}
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={file.name}>
                              {file.name}
                            </div>
                            <div style={{ display: 'flex', gap: '12px', marginTop: '4px', color: 'var(--text-muted)', fontSize: '0.78rem', flexWrap: 'wrap' }}>
                              <span>{formatFileSize(file.size)}</span>
                              {file.last_modified && (
                                <span>{formatRelativeTime(file.last_modified)}</span>
                              )}
                            </div>
                          </div>

                          {/* Action buttons */}
                          <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                            <button
                              onClick={() => handlePreviewFile(file.object_key)}
                              disabled={previewLoading && previewKey !== file.object_key}
                              title={previewKey === file.object_key ? 'Đóng phát lại' : 'Phát lại'}
                              style={{ margin: 0, padding: '7px 14px', fontSize: '0.8rem', background: previewKey === file.object_key ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)', border: `1px solid ${previewKey === file.object_key ? 'rgba(16,185,129,0.4)' : 'var(--glass-border)'}`, borderRadius: '8px', color: previewKey === file.object_key ? '#10b981' : 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}
                            >
                              {previewKey === file.object_key ? (
                                <><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Đóng</>
                              ) : (
                                <><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg> Phát</>
                              )}
                            </button>
                            <button
                              onClick={() => handleDeleteUserFile(file.object_key)}
                              title="Xóa file"
                              style={{ margin: 0, padding: '7px 10px', fontSize: '0.8rem', background: 'rgba(244,63,94,0.05)', border: '1px solid rgba(244,63,94,0.2)', borderRadius: '8px', color: 'var(--color-rose)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                              Xóa
                            </button>
                          </div>
                        </div>

                        {/* Audio player inline */}
                        {previewKey === file.object_key && previewUrl && (
                          <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '10px', border: '1px solid rgba(16,185,129,0.2)' }}>
                            <audio
                              controls
                              autoPlay
                              src={previewUrl}
                              style={{ width: '100%', height: '36px', accentColor: '#10b981' }}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : activeSessionId === null ? (
              /* State A: New Session (2 columns side-by-side with equal height) */
              <main className="dashboard new-session">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%' }}>
                  <AudioInputPanel
                    loading={loading}
                    disabled={false}
                    onAudioFromKey={handleAudioFromKey}
                    onText={handleTextSubmit}
                    onUploadFile={handleUploadFileOnly}
                  />
                </div>
                
                <section className="insights" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div className="card new-session-promo-card" style={{ padding: '60px 40px', textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', boxSizing: 'border-box' }}>
                    <div style={{ fontSize: '3rem', marginBottom: '20px' }}>🎙️</div>
                    <h3 style={{ fontSize: '1.4rem', fontWeight: '700', marginBottom: '12px' }}>
                      Bắt đầu phân tích cuộc gọi mới
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', maxWidth: '480px', margin: '0 auto 24px' }}>
                      Tải lên file âm thanh (.mp3, .wav), sử dụng ghi âm trực tiếp hoặc gửi văn bản transcript để đánh giá sắc thái cảm xúc AI Diarization.
                    </p>
                    <div style={{ display: 'inline-flex', gap: '8px', color: 'var(--text-muted)', fontSize: '0.85rem', justifyContent: 'center' }}>
                      <span>🚀 Tốc độ siêu tốc</span> • <span>🎯 Diarization chính xác</span> • <span>📊 Summary chi tiết</span>
                    </div>
                  </div>
                </section>
              </main>
            ) : (
              /* State B: Active Session (Single Centered Unified Column - Hides Input Panel & Centers All Results) */
              <main className="active-session-dashboard">
                <div className="active-session-centered-content">
                  {activeSessionDetail === null ? (
                    <div className="session-status-progress">
                      <div className="session-progress-spinner"></div>
                      <div className="session-progress-text">Đang tải thông tin session...</div>
                    </div>
                  ) : activeSessionDetail.status === 'pending' || activeSessionDetail.status === 'processing' ? (
                    <div className="card" style={{ padding: '40px', width: '100%', boxSizing: 'border-box' }}>
                      <div className="session-status-progress" style={{ padding: '20px 0' }}>
                        <div className="session-progress-spinner"></div>
                        <div className="session-progress-text">
                          {activeSessionDetail.status === 'pending'
                            ? 'Đang xếp hàng chờ xử lý...'
                            : 'Đang tiến hành phân tích cảm xúc cuộc gọi...'}
                        </div>
                        <div className="session-progress-sub">
                          Hệ thống đang chạy Voice Diarization & phân tích LLM. Vui lòng giữ kết nối.
                        </div>
                      </div>
                      <div style={{
                        width: '100%',
                        height: '8px',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: '99px',
                        overflow: 'hidden',
                        marginTop: '20px'
                      }}>
                        <div style={{
                          width: activeSessionDetail.status === 'pending' ? '25%' : '65%',
                          height: '100%',
                          background: 'linear-gradient(90deg, var(--color-primary) 0%, var(--color-teal) 100%)',
                          borderRadius: '99px',
                          transition: 'width 1s ease-in-out',
                          animation: 'pulse-glow 2s infinite ease-in-out'
                        }}></div>
                      </div>
                    </div>
                  ) : activeSessionDetail.status === 'failed' ? (
                    <div className="card" style={{ borderLeft: '6px solid var(--color-rose)', width: '100%', boxSizing: 'border-box', padding: '40px' }}>
                      <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                        <div style={{ fontSize: '2rem' }}>⚠️</div>
                        <div>
                          <h3 style={{ fontSize: '1.2rem', color: '#fff', fontWeight: '700', marginBottom: '8px' }}>
                            Phân tích thất bại
                          </h3>
                          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                            Đã có lỗi xảy ra trong quá trình xử lý:
                          </p>
                          <div className="error-panel" style={{ margin: '0 0 20px 0' }}>
                            {activeSessionDetail.error_message || 'Lỗi không xác định từ worker.'}
                          </div>
                          <button className="new-session-btn" style={{ width: 'auto' }} onClick={handleCreateNewSession}>
                            Thử lại với session mới
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Completed: Stack remaining results in a centered readable flow */
                    <>
                      <div className="status-header" style={{ width: '100%', boxSizing: 'border-box' }}>
                        <div className="status-title-section">
                          <span className="status-label">Tiến độ Job:</span>
                          <div className="status-badge completed">
                            <span className="status-indicator-dot"></span>
                            Đã hoàn thành
                          </div>
                        </div>
                        <div className="job-id-tag">
                          Job ID: <code>{activeSessionDetail.job_id}</code>
                        </div>
                      </div>

                      {error && <div className="error-panel" style={{ width: '100%', boxSizing: 'border-box' }}>{error}</div>}

                      {/* AI Agent Scorecard (if completed and has agent_score) */}
                      {activeSessionDetail.result?.agent_score !== undefined && activeSessionDetail.result?.agent_score !== null && (
                        <div className="agent-scorecard-card">
                          <div className="agent-scorecard-layout">
                            <div className="agent-score-ring-container">
                              <div className="agent-score-ring-svg">
                                <svg width="150" height="150" viewBox="0 0 100 100">
                                  <circle className="ring-bg" cx="50" cy="50" r="42" />
                                  <circle 
                                    className="ring-progress" 
                                    cx="50" 
                                    cy="50" 
                                    r="42" 
                                    stroke={
                                      activeSessionDetail.result.agent_score >= 80 ? '#10b981' :
                                      activeSessionDetail.result.agent_score >= 50 ? '#3b82f6' : '#ef4444'
                                    }
                                    strokeDasharray="263.9" 
                                    strokeDashoffset={263.9 - (activeSessionDetail.result.agent_score / 100) * 263.9} 
                                    style={{ filter: `drop-shadow(0 0 6px ${
                                      activeSessionDetail.result.agent_score >= 80 ? 'rgba(16,185,129,0.5)' :
                                      activeSessionDetail.result.agent_score >= 50 ? 'rgba(59,130,246,0.5)' : 'rgba(239,68,68,0.5)'
                                    })` }}
                                  />
                                </svg>
                                <div className="agent-score-text">
                                  <span className="agent-score-number">{activeSessionDetail.result.agent_score}</span>
                                  <span className="agent-score-label">Điểm số</span>
                                </div>
                              </div>
                              <div className="agent-status-label" style={{
                                color: activeSessionDetail.result.agent_score >= 80 ? '#10b981' :
                                       activeSessionDetail.result.agent_score >= 50 ? '#3b82f6' : '#ef4444'
                              }}>
                                {activeSessionDetail.result.agent_score >= 80 ? 'Xuất sắc' :
                                 activeSessionDetail.result.agent_score >= 50 ? 'Đạt yêu cầu' : 'Cần cải thiện'}
                              </div>
                            </div>
                            <div className="agent-advice-panel">
                              <div className="agent-advice-title">
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#eab308" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="advice-icon"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .6 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"></path><path d="M9 18h6"></path><path d="M10 22h4"></path></svg>
                                Đánh giá & Khuyến nghị của AI cho Nhân viên
                              </div>
                              <div className="advice-list">
                                {activeSessionDetail.result.agent_advice && activeSessionDetail.result.agent_advice.length > 0 ? (
                                  activeSessionDetail.result.agent_advice.map((adv, idx) => (
                                    <div key={idx} className="advice-item">
                                      <span className="advice-icon">💡</span>
                                      <span>{adv}</span>
                                    </div>
                                  ))
                                ) : (
                                  <div className="advice-item">
                                    <span className="advice-icon">💡</span>
                                    <span>Hội thoại diễn ra tốt đẹp, nhân viên ứng xử đúng mực và hỗ trợ khách hàng hiệu quả.</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Sentiment Badge (Top) */}
                      <SentimentBadge
                        sentiment={activeSessionDetail.result?.sentiment}
                        reason={activeSessionDetail.result?.sentiment_reason}
                        confidence={activeSessionDetail.result?.confidence}
                      />

                      {/* Summary Card (Middle) */}
                      <SummaryCard items={activeSessionDetail.result?.summary ?? []} />

                      {/* Premium Call Playback Center (New) */}
                      {sessionAudioUrl && (
                        <div className="card shadow-animated" style={{
                          width: '100%',
                          boxSizing: 'border-box',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px',
                          background: 'linear-gradient(135deg, rgba(31,41,55,0.4) 0%, rgba(17,24,39,0.6) 100%)',
                          border: '1px solid rgba(16,185,129,0.15)',
                          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
                          borderRadius: '16px',
                          padding: '16px 20px',
                          transition: 'all 0.3s ease',
                          marginTop: '8px'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: '36px',
                              height: '36px',
                              borderRadius: '50%',
                              background: 'rgba(16, 185, 129, 0.1)',
                              border: '1px solid rgba(16, 185, 129, 0.25)',
                              color: '#10b981',
                              animation: 'pulse-glow 2s infinite'
                            }}>
                              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>Nghe lại ghi âm cuộc hội thoại</span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Vừa phát ghi âm vừa đối chiếu nhanh với nội dung Transcript bên dưới</span>
                            </div>
                          </div>
                          <div style={{ width: '100%', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                            <audio
                              controls
                              src={sessionAudioUrl}
                              style={{ width: '100%', height: '40px', accentColor: '#10b981' }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Transcript Log (Bottom) */}
                      <TranscriptLog turns={activeSessionDetail.result?.transcript ?? []} />

                      {/* Completed banner and new session button */}
                      <div className="session-completed-banner" style={{ width: '100%', boxSizing: 'border-box', marginTop: '8px' }}>
                        <span className="session-completed-text">
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-teal)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                          Phân tích hoàn tất! Hãy tạo mới session để nhận job phân tích tiếp theo.
                        </span>
                        <button className="session-completed-btn" onClick={handleCreateNewSession}>
                          Tạo session mới
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </main>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
