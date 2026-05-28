import React from 'react';
import { useRegister } from '../hooks/useRegister';

interface RegisterPageProps {
  onSwitchToLogin: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onSwitchToLogin }) => {
  const {
    username,
    setUsername,
    email,
    setEmail,
    password,
    setPassword,
    confirmPassword,
    setConfirmPassword,
    isSubmitting,
    successMsg,
    setSuccessMsg,
    setLocalError,
    clearError,
    displayError,
    handleSubmit,
  } = useRegister();

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
          <h2>Đăng Ký Tài Khoản</h2>
          {displayError && (
            <div className="auth-error">
              <span>{displayError}</span>
              <button type="button" onClick={() => { setLocalError(null); clearError(); }} className="error-close-btn">&times;</button>
            </div>
          )}
          {successMsg && (
            <div className="auth-success">
              <span>{successMsg}</span>
              <button type="button" onClick={() => setSuccessMsg(null)} className="error-close-btn">&times;</button>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="username">Tên tài khoản</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Tối thiểu 3 ký tự..."
              required
              className="auth-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Địa chỉ Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="example@mail.com..."
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
              placeholder="Tối thiểu 6 ký tự..."
              required
              className="auth-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Xác nhận mật khẩu</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Nhập lại mật khẩu..."
              required
              className="auth-input"
            />
          </div>

          <button type="submit" disabled={isSubmitting} className="auth-btn">
            {isSubmitting ? 'Đang đăng ký...' : 'Đăng Ký'}
          </button>
        </form>

        <div className="auth-footer">
          Đã có tài khoản?{' '}
          <button type="button" onClick={onSwitchToLogin} className="link-btn">
            Đăng nhập ngay
          </button>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
