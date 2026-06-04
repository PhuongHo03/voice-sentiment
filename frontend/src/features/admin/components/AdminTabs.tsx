import React from 'react';
import type { AdminTab } from '../states/adminState';

interface AdminTabsProps {
  activeTab: AdminTab;
  handleSetActiveTab: (tab: AdminTab) => void;
  pendingCount: number;
}

export const AdminTabs: React.FC<AdminTabsProps> = ({ activeTab, handleSetActiveTab, pendingCount }) => {
  return (
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
      <button
        className={`admin-tab-btn ${activeTab === 'metrics' ? 'active' : ''}`}
        onClick={() => handleSetActiveTab('metrics')}
        id="tab-metrics"
      >
        📈 Metrics hệ thống
      </button>
      <button
        className={`admin-tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
        onClick={() => handleSetActiveTab('logs')}
        id="tab-logs"
      >
        📄 Logs hệ thống
      </button>
    </nav>
  );
};
