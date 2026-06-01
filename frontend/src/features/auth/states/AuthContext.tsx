import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchCurrentUser, loginRequest, registerRequest } from '../api/authApi';
import type { AuthContextType, User } from '../types/auth';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

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
          const userData = await fetchCurrentUser(storedToken);
          if (userData) {
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
      const data = await loginRequest(email, password);
      localStorage.setItem('voice_sentiment_token', data.access_token);
      setToken(data.access_token);

      // Fetch user profile immediately
      const userData = await fetchCurrentUser(data.access_token);
      if (userData) {
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
      await registerRequest(username, email, password, roleId);
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
