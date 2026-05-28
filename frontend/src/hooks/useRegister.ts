import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export function useRegister() {
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

  return {
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
    localError,
    setLocalError,
    clearError,
    displayError,
    handleSubmit,
  };
}
