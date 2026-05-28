import React, { createContext, useContext, useState, useEffect } from 'react';

export interface Role {
  id: string;
  name: string;
  description?: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role_id: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (username: string, email: string, password: string, roleId?: string) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper to format/translate Pydantic/FastAPI validation or system errors
function parseDetailError(detail: any, defaultMsg: string): string {
  if (!detail) return defaultMsg;
  
  if (typeof detail === 'string') {
    if (detail === 'Incorrect email or password') return 'Mật khẩu hoặc email không chính xác!';
    if (detail === 'User is not active') return 'Tài khoản chưa được kích hoạt bởi Ban quản trị!';
    if (detail === 'Email already registered') return 'Địa chỉ email đã tồn tại trong hệ thống!';
    if (detail === 'Username already registered') return 'Tên tài khoản đã tồn tại trong hệ thống!';
    return detail;
  }
  
  if (Array.isArray(detail)) {
    const err = detail[0];
    if (err && typeof err === 'object') {
      const msg = err.msg || '';
      if (msg.includes('value is not a valid email address')) {
        return 'Địa chỉ email không đúng định dạng!';
      }
      return err.msg || JSON.stringify(err);
    }
    return detail.map(d => typeof d === 'object' ? JSON.stringify(d) : String(d)).join(', ');
  }
  
  if (typeof detail === 'object') {
    return detail.message || JSON.stringify(detail);
  }
  
  return String(detail);
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Auto load user if token exists in localStorage
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('voice_sentiment_token');
      if (storedToken) {
        try {
          const response = await fetch('/api/auth/me', {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });
          
          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
            setToken(storedToken);
          } else {
            // Token expired or invalid
            localStorage.removeItem('voice_sentiment_token');
          }
        } catch (err) {
          console.error('Failed to restore auth session:', err);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errorDetail = parseDetailError(errorData.detail, 'Incorrect email or password');
        throw new Error(errorDetail);
      }

      const data = await response.json();
      localStorage.setItem('voice_sentiment_token', data.access_token);
      setToken(data.access_token);

      // Fetch user profile immediately
      const meResponse = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${data.access_token}`
        }
      });

      if (meResponse.ok) {
        const userData = await meResponse.json();
        setUser(userData);
        setIsLoading(false);
        return true;
      } else {
        throw new Error('Failed to fetch user profile after login');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed');
      setIsLoading(false);
      return false;
    }
  };

  const register = async (username: string, email: string, password: string, roleId = 'employee'): Promise<boolean> => {
    setError(null);
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, email, password, role_id: roleId }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errorDetail = parseDetailError(errorData.detail, 'Registration failed');
        throw new Error(errorDetail);
      }

      return true;
    } catch (err: any) {
      setError(err.message || 'Registration failed');
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('voice_sentiment_token');
    localStorage.removeItem('activeView');
    localStorage.removeItem('activeSessionId');
    setUser(null);
    setToken(null);
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        login,
        register,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
