import { useState } from 'react';
import { useAuth } from '../states/AuthContext';

export function useLogin() {
  const { login, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setLocalError(null);
    clearError();

    // Regular expression for basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setLocalError('Địa chỉ email không đúng định dạng!');
      return;
    }

    setIsSubmitting(true);
    await login(email, password);
    setIsSubmitting(false);
  };

  const handleClearError = () => {
    setLocalError(null);
    clearError();
  };

  const displayError = localError || error;

  return {
    email,
    setEmail,
    password,
    setPassword,
    isSubmitting,
    error: displayError,
    clearError: handleClearError,
    handleSubmit,
  };
}
