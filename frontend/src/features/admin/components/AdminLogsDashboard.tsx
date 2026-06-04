import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../auth/states/AuthContext';
import { fetchWorkerLogsRequest } from '../api/adminApi';

export const AdminLogsDashboard: React.FC = () => {
  const { token } = useAuth();
  const [worker, setWorker] = useState<string>('llm-worker');
  const [lines, setLines] = useState<number>(100);
  const [logs, setLogs] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [refreshInterval, setRefreshInterval] = useState<number>(5000); // 5 seconds default

  const terminalRef = useRef<HTMLDivElement>(null);

  const loadLogs = useCallback(async (showSpinner = true) => {
    if (!token) return;
    if (showSpinner) setIsLoading(true);
    setError(null);
    try {
      const data = await fetchWorkerLogsRequest(token, worker, lines);
      setLogs(data.logs || '');
    } catch (err: any) {
      setError(err.message || 'Lỗi khi tải logs');
    } finally {
      if (showSpinner) setIsLoading(false);
    }
  }, [token, worker, lines]);

  // Initial load and worker/lines change load
  useEffect(() => {
    loadLogs(true);
  }, [loadLogs]);

  // Auto refresh interval loop
  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      loadLogs(false);
    }, refreshInterval);
    return () => clearInterval(timer);
  }, [autoRefresh, refreshInterval, loadLogs]);

  // Auto-scroll to bottom of terminal when logs update
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // Format log lines with color coding
  const renderLogLines = () => {
    if (!logs) return <div className="log-empty">Không có dữ liệu logs hoặc file rỗng.</div>;

    const linesArray = logs.split('\n');
    const filteredLines = linesArray.filter(line => 
      line.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (filteredLines.length === 0 && searchQuery) {
      return <div className="log-empty">Không tìm thấy dòng log nào khớp với từ khóa "{searchQuery}"</div>;
    }

    return filteredLines.map((line, idx) => {
      let className = 'log-line';
      if (line.includes('[INFO]')) {
        className += ' info';
      } else if (line.includes('[WARNING]') || line.includes('[WARN]')) {
        className += ' warn';
      } else if (line.includes('[ERROR]') || line.includes('Error') || line.includes('Exception') || line.includes('Traceback')) {
        className += ' error';
      } else if (line.toLowerCase().includes('success') || line.includes('successfully')) {
        className += ' success';
      }

      return (
        <div key={idx} className={className}>
          {line}
        </div>
      );
    });
  };

  return (
    <div className="logs-mgmt-layout animate-fade-in">
      <div className="section-header-row">
        <h2>📄 Nhật ký Hệ thống (Logs)</h2>
        <button 
          className="refresh-btn" 
          onClick={() => loadLogs(true)} 
          disabled={isLoading}
        >
          {isLoading ? <span className="btn-spinner"></span> : '🔄 Làm mới'}
        </button>
      </div>

      {/* Control Filters */}
      <div className="logs-control-panel">
        <div className="logs-filters">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>DỊCH VỤ WORKER</label>
            <select 
              className="logs-select"
              value={worker}
              onChange={(e) => setWorker(e.target.value)}
            >
              <option value="llm-worker">🧠 LLM Worker (Phân tích & Chấm điểm)</option>
              <option value="voice-worker">🎙️ Voice Worker (ASR - Nhận dạng giọng nói)</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>SỐ DÒNG XEM GẦN NHẤT</label>
            <select 
              className="logs-select"
              value={lines}
              onChange={(e) => setLines(Number(e.target.value))}
            >
              <option value={50}>50 dòng</option>
              <option value={100}>100 dòng</option>
              <option value={200}>200 dòng</option>
              <option value={500}>500 dòng</option>
              <option value={1000}>1000 dòng</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', width: '220px' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>LỌC NỘI DUNG LOGS</label>
            <input
              type="text"
              placeholder="Tìm kiếm từ khóa..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="logs-select"
              style={{ width: '100%', boxSizing: 'border-box' }}
            />
          </div>
        </div>

        {/* Auto Refresh Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <label className="logs-auto-refresh">
            <input 
              type="checkbox" 
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Tự động làm mới</span>
          </label>

          {autoRefresh && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <select
                className="logs-select"
                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
              >
                <option value={3000}>Mỗi 3 giây</option>
                <option value={5000}>Mỗi 5 giây</option>
                <option value={10000}>Mỗi 10 giây</option>
                <option value={30000}>Mỗi 30 giây</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="card text-rose" style={{ padding: '14px 20px', border: '1px solid rgba(244, 63, 94, 0.25)', background: 'rgba(244, 63, 94, 0.05)', borderRadius: '12px' }}>
          ⚠️ <strong>Lỗi:</strong> {error}
        </div>
      )}

      {/* Terminal Screen Container */}
      <div className="logs-terminal-container" ref={terminalRef}>
        {isLoading && logs === '' ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '12px' }}>
            <div className="loader"></div>
            <p style={{ color: 'var(--text-secondary)' }}>Đang kết nối để đọc log...</p>
          </div>
        ) : (
          renderLogLines()
        )}
      </div>
    </div>
  );
};
