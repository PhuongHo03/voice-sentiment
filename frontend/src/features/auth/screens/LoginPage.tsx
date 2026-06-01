import React from 'react';
import { AuthLayout } from '../components/AuthLayout';
import { AuthMessage } from '../components/AuthMessage';
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
    <AuthLayout
      footer={(
        <>
          Chưa có tài khoản?{' '}
          <button type="button" onClick={onSwitchToRegister} className="link-btn">
            Đăng ký ngay
          </button>
        </>
      )}
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <h2>Đăng Nhập</h2>
        {error && <AuthMessage type="error" message={error} onClose={clearError} />}

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
    </AuthLayout>
  );
};

export default LoginPage;
