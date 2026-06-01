import React from 'react';

interface AuthLayoutProps {
  children: React.ReactNode;
  footer: React.ReactNode;
}

export function AuthLayout({ children, footer }: AuthLayoutProps) {
  return (
    <div className="auth-container">
      <div className="auth-card card">
        <div className="auth-header">
          <div className="auth-logo">
            <span className="live-indicator"></span>
            <h1>VOICE SENTIMENT</h1>
          </div>
          <p className="auth-subtitle">Hệ thống phân tích cảm xúc & hiệu suất cuộc gọi</p>
        </div>

        {children}

        <div className="auth-footer">
          {footer}
        </div>
      </div>
    </div>
  );
}
