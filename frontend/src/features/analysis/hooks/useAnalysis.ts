import { useCallback, useEffect, useState } from 'react';
import {
  deleteSession,
  fetchSessions,
  getAnalysis,
  renameSession,
  submitAudioFromKey,
  submitText,
  fetchStats,
  listUserFiles,
  deleteUserFile,
  uploadFileOnly,
} from '../api/analysisApi';
import {
  createUploadedFileItem,
  getInitialAnalysisView,
  getStoredActiveSessionId,
  getStoredActiveView,
  persistActiveSessionId,
  persistActiveView,
  resolveInitialActiveSessionId,
  type AnalysisView,
} from '../states/analysisState';
import type { JobStatus, MinioFile, SessionListItem, UploadOnlyResult } from '../types/analysis';

export function useDashboardAnalysis(isAdmin: boolean = false) {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSessionDetail, setActiveSessionDetail] = useState<JobStatus | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  // Layout & View Navigation State
  const [activeView, setActiveView] = useState<AnalysisView>(
    () => getInitialAnalysisView(getStoredActiveView())
  );
  const [stats, setStats] = useState<any>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Inline renaming state
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // MinIO File Storage state
  const [userFiles, setUserFiles] = useState<MinioFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [filesError, setFilesError] = useState<string | null>(null);

  // Helper to persist active session ID
  function setActiveSessionIdPersisted(id: string | null) {
    persistActiveSessionId(id);
    setActiveSessionId(id);
  }

  // Helper to persist active view
  function setActiveViewPersisted(view: AnalysisView) {
    persistActiveView(view);
    setActiveView(view);
  }

  // Load stats for Dashboard view
  async function loadStats() {
    setStatsLoading(true);
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (err) {
      console.error('Lỗi tải stats:', err);
    } finally {
      setStatsLoading(false);
    }
  }

  // Load user files from MinIO
  const loadUserFiles = useCallback(async () => {
    setFilesLoading(true);
    setFilesError(null);
    try {
      const data = await listUserFiles();
      setUserFiles(data.files);
    } catch (err) {
      console.error('Lỗi tải file từ MinIO:', err);
      setFilesError(err instanceof Error ? err.message : 'Không thể tải danh sách file');
    } finally {
      setFilesLoading(false);
    }
  }, []);

  // 1. Fetch sessions list on mount
  useEffect(() => {
    async function loadSessions() {
      setSessionsLoading(true);
      try {
        const response = await fetchSessions(50, 0);
        const sessionsData = response.sessions;
        setSessions(sessionsData);
        setActiveSessionId(resolveInitialActiveSessionId(
          sessionsData,
          getStoredActiveSessionId(),
          getStoredActiveView()
        ));
      } catch (err) {
        console.error('Không thể tải lịch sử session:', err);
      } finally {
        setSessionsLoading(false);
      }
    }
    loadSessions();
  }, []);

  // 2. Fetch active session details when ID changes
  useEffect(() => {
    const currentId = activeSessionId;
    if (!currentId) {
      setActiveSessionDetail(null);
      return;
    }

    let isMounted = true;
    async function loadDetail() {
      try {
        const detail = await getAnalysis(currentId as string);
        if (isMounted) {
          setActiveSessionDetail(detail);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Không thể tải chi tiết session');
        }
      }
    }

    loadDetail();
    return () => {
      isMounted = false;
    };
  }, [activeSessionId]);

  // 3. Polling active pending/processing sessions in background
  useEffect(() => {
    const hasRunning = sessions.some(s => s.status === 'pending' || s.status === 'processing');
    if (!hasRunning) return;

    const timer = setInterval(() => {
      const runningIds = sessions
        .filter(s => s.status === 'pending' || s.status === 'processing')
        .map(s => s.job_id);

      runningIds.forEach(async (id) => {
        try {
          const updated = await getAnalysis(id);
          
          // Update sessions list state
          setSessions(prev => {
            const match = prev.find(item => item.job_id === id);
            if (!match || match.status === updated.status) return prev;

            return prev.map(item => {
              if (item.job_id === id) {
                return {
                  ...item,
                  status: updated.status,
                  sentiment: updated.result?.sentiment ?? null,
                  confidence: updated.result?.confidence ?? null,
                };
              }
              return item;
            });
          });

          // Update active session detail state if it's the one that changed
          if (activeSessionId === id) {
            setActiveSessionDetail(prev => {
              if (prev?.status === updated.status && JSON.stringify(prev?.result) === JSON.stringify(updated.result)) {
                return prev;
              }
              return updated;
            });
          }

          // Trigger stats reload if a job has completed
          if (updated.status === 'completed' && activeView === 'dashboard') {
            loadStats();
          }
        } catch (err) {
          console.error(`Lỗi poll session ${id}:`, err);
        }
      });
    }, 2000);

    return () => clearInterval(timer);
  }, [sessions, activeSessionId, activeView]);

  // Load stats when dashboard view is opened
  useEffect(() => {
    if (activeView === 'dashboard') {
      loadStats();
    }
    if (activeView === 'files') {
      loadUserFiles();
    }
  }, [activeView]);

  // Upload file to MinIO only (no analysis), then refresh file list
  async function handleUploadFileOnly(file: File): Promise<UploadOnlyResult> {
    const result = await uploadFileOnly(file);
    // Optimistically prepend the new file to the list so UI updates immediately
    setUserFiles(prev => [createUploadedFileItem(result), ...prev]);
    return result;
  }

  // Create new session
  function handleCreateNewSession() {
    setActiveViewPersisted('session');
    setActiveSessionIdPersisted(null);
    setActiveSessionDetail(null);
    setError(null);
  }

  // Submit Audio from already-uploaded MinIO key (no re-upload)
  async function handleAudioFromKey(objectKey: string, fileName: string) {
    setLoading(true);
    setError(null);
    try {
      const job = await submitAudioFromKey(objectKey, fileName);

      const newSessionItem: SessionListItem = {
        job_id: job.job_id,
        name: fileName,
        status: 'pending',
        input_type: 'audio',
        created_at: new Date().toISOString(),
        sentiment: null,
        confidence: null,
      };

      setSessions(prev => [newSessionItem, ...prev]);
      setActiveSessionIdPersisted(job.job_id);
      setActiveSessionDetail(job);
      setActiveViewPersisted('session');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gửi phân tích thất bại');
    } finally {
      setLoading(false);
    }
  }

  // Submit Audio (legacy - upload + analyze in one step)
  async function handleAudioSubmit(file: File) {
    setLoading(true);
    setError(null);
    try {
      // Step 1: upload-only to MinIO
      const uploaded = await uploadFileOnly(file);
      // Optimistically add to file list
      setUserFiles(prev => [createUploadedFileItem(uploaded), ...prev]);

      // Step 2: create analysis job from key
      const job = await submitAudioFromKey(uploaded.object_key, file.name);

      const newSessionItem: SessionListItem = {
        job_id: job.job_id,
        name: file.name,
        status: 'pending',
        input_type: 'audio',
        created_at: new Date().toISOString(),
        sentiment: null,
        confidence: null,
      };

      setSessions(prev => [newSessionItem, ...prev]);
      setActiveSessionIdPersisted(job.job_id);
      setActiveSessionDetail(job);
      setActiveViewPersisted('session');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Tải lên và gửi phân tích thất bại');
    } finally {
      setLoading(false);
    }
  }

  // Submit Text
  async function handleTextSubmit(text: string) {
    setLoading(true);
    setError(null);
    try {
      const job = await submitText(text);
      const snippet = text.slice(0, 60) + (text.length > 60 ? '...' : '');
      
      const newSessionItem: SessionListItem = {
        job_id: job.job_id,
        name: snippet,
        status: 'pending',
        input_type: 'text',
        created_at: new Date().toISOString(),
        sentiment: null,
        confidence: null,
      };

      setSessions(prev => [newSessionItem, ...prev]);
      setActiveSessionIdPersisted(job.job_id);
      setActiveSessionDetail(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gửi văn bản thất bại');
    } finally {
      setLoading(false);
    }
  }

  // Rename Session
  async function handleSaveRename(id: string) {
    if (!editingName.trim()) return;
    try {
      await renameSession(id, editingName.trim());
      setSessions(prev => prev.map(s => s.job_id === id ? { ...s, name: editingName.trim() } : s));
      if (activeSessionDetail?.job_id === id) {
        setActiveSessionDetail(prev => prev ? { ...prev, name: editingName.trim() } : null);
      }
      setEditingSessionId(null);
    } catch (err) {
      alert('Không thể đổi tên session: ' + (err instanceof Error ? err.message : 'Lỗi không xác định'));
    }
  }

  // Delete Session
  async function handleDeleteSession(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm('Bạn có chắc chắn muốn xóa session này cùng tất cả kết quả phân tích?')) return;
    try {
      await deleteSession(id);
      const updated = sessions.filter(s => s.job_id !== id);
      setSessions(updated);
      
      if (activeSessionId === id) {
        if (updated.length > 0) {
          setActiveSessionIdPersisted(updated[0].job_id);
        } else {
          setActiveSessionIdPersisted(null);
          setActiveSessionDetail(null);
        }
      }
      
      if (activeView === 'dashboard') {
        loadStats();
      }
    } catch (err) {
      alert('Không thể xóa session: ' + (err instanceof Error ? err.message : 'Lỗi không xác định'));
    }
  }

  // Delete user file from MinIO
  async function handleDeleteUserFile(objectKey: string) {
    if (!confirm('Bạn có chắc chắn muốn xóa file này khỏi kho lưu trữ?')) return;
    try {
      await deleteUserFile(objectKey);
      setUserFiles(prev => prev.filter(f => f.object_key !== objectKey));
    } catch (err) {
      alert('Không thể xóa file: ' + (err instanceof Error ? err.message : 'Lỗi không xác định'));
    }
  }

  // Helper to format date relatively in Vietnamese
  function formatRelativeTime(dateStr: string) {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'Vừa xong';
      if (diffMins < 60) return `${diffMins} phút trước`;
      if (diffHours < 24) return `${diffHours} giờ trước`;
      return `${diffDays} ngày trước`;
    } catch (e) {
      return '';
    }
  }

  // Helper to format file size
  function formatFileSize(bytes: number | null): string {
    if (bytes === null || bytes === undefined) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  // Helper to get dominant sentiment label
  function getDominantSentiment(dist: any) {
    if (!dist) return 'N/A';
    const pos = dist.positive || 0;
    const neu = dist.neutral || 0;
    const neg = dist.negative || 0;
    if (pos === 0 && neu === 0 && neg === 0) return 'Chưa có';
    if (pos >= neu && pos >= neg) return 'Tích cực';
    if (neu >= pos && neu >= neg) return 'Trung lập';
    return 'Tiêu cực';
  }

  // Filter sessions by search query
  const filteredSessions = sessions.filter(s => 
    (s.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (s.job_id || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return {
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
  };
}
