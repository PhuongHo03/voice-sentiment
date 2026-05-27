import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface RegisterPageProps {
  onSwitchToLogin: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onSwitchToLogin }) => {
  const { register, error, clearError } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !email || !password || !confirmPassword) return;
    
    setLocalError(null);
    clearError();
    setSuccessMsg(null);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(email)) {
      setLocalError('Địa chỉ email không đúng định dạng!');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('Mật khẩu xác nhận không trùng khớp!');
      return;
    }

    setIsSubmitting(true);
    
    const success = await register(username, email, password, 'employee');
    setIsSubmitting(false);
    
    if (success) {
      setSuccessMsg('Đăng ký tài khoản thành công! Vui lòng chờ Ban quản trị kích hoạt tài khoản của bạn trước khi đăng nhập.');
      setUsername('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
    }
  };


  const getErrorMessage = () => {
    if (localError) return localError;
    if (!error) return null;
    if (error === 'Email already registered') {
      return 'Địa chỉ email đã tồn tại trong hệ thống!';
    }
    if (error === 'Username already registered') {
      return 'Tên tài khoản đã tồn tại trong hệ thống!';
    }
    return error;
  };

  const displayError = getErrorMessage();

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
