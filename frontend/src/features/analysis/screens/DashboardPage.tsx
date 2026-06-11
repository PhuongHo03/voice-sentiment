import { useState } from 'react';
import { AudioInputPanel } from '../components/audio/AudioInputPanel';
import { SessionDetailPanel } from '../../../shared/components/session/SessionDetailPanel';
import { PerformanceDashboardPanel } from '../../../shared/components/performance/PerformanceDashboardPanel';
import { useAuth } from '../../auth/states/AuthContext';
import { useDashboardAnalysis } from '../hooks/useAnalysis';
import { getFilePresignedUrl } from '../api/analysisApi';

export function DashboardPage({ isAdmin = false, onGoToAdmin }: { isAdmin?: boolean; onGoToAdmin?: () => void }) {
  const { logout, user, token } = useAuth();
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
    loadStats,
    // MinIO file management
    userFiles,
    filesTotal,
    filesLoading,
    filesError,
    loadUserFiles,
    handleDeleteUserFile,
  } = useDashboardAnalysis(token, isAdmin);

  // Audio preview state for the Files view
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';
  const sessionAudioUrl = activeSessionDetail?.audio_object_key
    ? `${apiBaseUrl}/api/files/stream?object_key=${encodeURIComponent(activeSessionDetail.audio_object_key)}&token=${encodeURIComponent(token ?? '')}`
    : null;
  const activeSessionViewModel = activeSessionDetail
    ? {
        jobId: activeSessionDetail.job_id,
        name: activeSessionDetail.name,
        status: activeSessionDetail.status,
        inputType: activeSessionDetail.input_type,
        errorMessage: activeSessionDetail.error_message,
        audioUrl: sessionAudioUrl,
        result: activeSessionDetail.result,
      }
    : null;

  async function handlePreviewFile(objectKey: string) {
    if (previewKey === objectKey) {
      setPreviewUrl(null);
      setPreviewKey(null);
      return;
    }
    setPreviewLoading(true);
    try {
      const url = getFilePresignedUrl(objectKey, token);
      setPreviewUrl(url);
      setPreviewKey(objectKey);
    } catch (e) {
      alert('Không thể tải link phát lại: ' + (e instanceof Error ? e.message : 'Lỗi'));
    } finally {
      setPreviewLoading(false);
    }
  }

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
                  {filesTotal > 0 && (
                    <span style={{ marginLeft: 'auto', background: 'rgba(139,92,246,0.2)', color: 'var(--color-primary)', borderRadius: '99px', fontSize: '0.7rem', padding: '1px 6px', fontWeight: 700 }}>{filesTotal}</span>
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
                {filesTotal > 0 && (
                  <span style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-4px',
                    minWidth: '16px',
                    height: '16px',
                    padding: '0 4px',
                    background: 'var(--color-primary)',
                    color: '#fff',
                    borderRadius: '99px',
                    fontSize: '0.62rem',
                    fontWeight: 800,
                    lineHeight: '16px',
                    textAlign: 'center',
                    boxShadow: '0 0 0 2px rgba(10, 10, 18, 0.95)',
                  }}>
                    {filesTotal > 99 ? '99+' : filesTotal}
                  </span>
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
                <PerformanceDashboardPanel
                  stats={stats}
                  sessions={sessions}
                  loading={statsLoading && !stats}
                  onSessionClick={(session) => {
                    setActiveSessionIdPersisted(session.job_id);
                    setActiveViewPersisted('session');
                  }}
                />
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
                  ) : activeSessionViewModel ? (
                    <SessionDetailPanel
                      session={activeSessionViewModel}
                      variant="inline"
                      error={error}
                      onCreateNewSession={handleCreateNewSession}
                    />
                  ) : null}
                </div>
              </main>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
