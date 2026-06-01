import React from 'react';

interface AdminHeaderProps {
  username?: string;
  onBackToPersonal: () => void;
  logout: () => void;
}

export const AdminHeader: React.FC<AdminHeaderProps> = ({ username, onBackToPersonal, logout }) => {
  return (
    <header className="admin-header">
      <div className="admin-logo-sec">
        <span className="live-indicator"></span>
        <h2>VOICE SENTIMENT <span className="admin-pill">Admin Portal</span></h2>
      </div>
      <div className="admin-nav-actions">
        <span className="admin-user-info">Chào, <strong>{username}</strong></span>
        <button onClick={onBackToPersonal} className="nav-btn secondary-btn">
          📂 Chế độ cá nhân
        </button>
        <button onClick={logout} className="nav-btn danger-btn">
          🚪 Đăng xuất
        </button>
      </div>
    </header>
  );
};
