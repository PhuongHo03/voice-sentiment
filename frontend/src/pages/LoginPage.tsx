import React from 'react';
import { useLogin } from '../hooks/useLogin';

interface LoginPageProps {
  onSwitchToRegister: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onSwitchToRegister }) => {
  const {
    email,
    setEmail,
    password,
    setPassword,
    isSubmitting,
    error,
    clearError,
    handleSubmit,
  } = useLogin();

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

        <form onSubmit={handleSubmit} className="auth-form">
          <h2>Đăng Nhập</h2>
          {error && (
            <div className="auth-error">
              <span>{error}</span>
              <button type="button" onClick={clearError} className="error-close-btn">&times;</button>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Nhập địa chỉ email..."
              required
              className="auth-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Mật khẩu</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Nhập mật khẩu..."
              required
              className="auth-input"
            />
          </div>

          <button type="submit" disabled={isSubmitting} className="auth-btn">
            {isSubmitting ? 'Đang xác thực...' : 'Đăng Nhập'}
          </button>
        </form>

        <div className="auth-footer">
          Chưa có tài khoản?{' '}
          <button type="button" onClick={onSwitchToRegister} className="link-btn">
            Đăng ký ngay
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
