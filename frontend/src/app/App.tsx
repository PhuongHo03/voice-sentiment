import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from '../features/auth/states/AuthContext';
import { DashboardPage } from '../features/analysis/screens/DashboardPage';
import { LoginPage } from '../features/auth/screens/LoginPage';
import { RegisterPage } from '../features/auth/screens/RegisterPage';
import { AdminDashboardPage } from '../features/admin/screens/AdminDashboardPage';
import '../styles/main.css';

function AppContent() {
  const { user, isLoading } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [viewMode, setViewMode] = useState<'personal' | 'admin'>(() => {
    // Check URL first
    if (window.location.pathname.startsWith('/admin')) {
      return 'admin';
    }
    const saved = localStorage.getItem('view_mode');
    return (saved === 'admin') ? 'admin' : 'personal';
  });

  // Sync state with URL history
  const handleSetViewMode = (mode: 'personal' | 'admin') => {
    setViewMode(mode);
    localStorage.setItem('view_mode', mode);
    
    if (mode === 'admin') {
      const activeTab = localStorage.getItem('admin_active_tab') || 'performance';
      const newPath = activeTab === 'accounts'
        ? '/admin/accounts'
        : activeTab === 'observability'
          ? '/admin/observability'
          : '/admin/employees';
      if (window.location.pathname !== newPath) {
        window.history.pushState({ mode, activeTab }, '', newPath);
      }
    } else {
      if (window.location.pathname !== '/') {
        window.history.pushState({ mode }, '', '/');
      }
    }
  };

  // Listen to popstate event (browser Back/Forward buttons)
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      if (path.startsWith('/admin')) {
        setViewMode('admin');
        localStorage.setItem('view_mode', 'admin');
      } else {
        setViewMode('personal');
        localStorage.setItem('view_mode', 'personal');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  if (isLoading) {
    return (
      <div className="auth-container">
        <div className="auth-card card text-center">
          <div className="loader" style={{ margin: '30px auto' }}></div>
          <h3>Đang xác thực thông tin...</h3>
          <p className="text-secondary">Vui lòng chờ trong giây lát</p>
        </div>
      </div>
    );
  }

  // Not logged in -> show login or register page
  if (!user) {
    if (isRegister) {
      return <RegisterPage onSwitchToLogin={() => setIsRegister(false)} />;
    }
    return <LoginPage onSwitchToRegister={() => setIsRegister(true)} />;
  }

  // Logged in and selected Admin Mode -> show Admin Dashboard
  if (viewMode === 'admin' && user.role_id === 'admin') {
    return <AdminDashboardPage onBackToPersonal={() => handleSetViewMode('personal')} />;
  }

  // Default: show Personal Dashboard Page
  return (
    <DashboardPage 
      isAdmin={user.role_id === 'admin'} 
      onGoToAdmin={() => handleSetViewMode('admin')} 
    />
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
