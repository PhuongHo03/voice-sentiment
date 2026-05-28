import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import type { Employee, EmployeeStats, EmployeeSession, AccountUser } from '../types/admin';

export function useAdminDashboard() {
  const { token, logout, user } = useAuth();

  // Tab state: 'performance' | 'accounts'
  const [activeTab, setActiveTab] = useState<'performance' | 'accounts'>(() => {
    const path = window.location.pathname;
    if (path === '/admin/accounts') return 'accounts';
    if (path === '/admin/employees') return 'performance';
    const saved = localStorage.getItem('admin_active_tab');
    return (saved === 'accounts') ? 'accounts' : 'performance';
  });

  const handleSetActiveTab = (tab: 'performance' | 'accounts') => {
    setActiveTab(tab);
    localStorage.setItem('admin_active_tab', tab);
    const newPath = tab === 'accounts' ? '/admin/accounts' : '/admin/employees';
    if (window.location.pathname !== newPath) {
      window.history.pushState({ mode: 'admin', activeTab: tab }, '', newPath);
    }
  };

  // ── Performance tab state ──
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selectedEmp, setSelectedEmp] = useState<Employee | null>(null);
  const [empStats, setEmpStats] = useState<EmployeeStats | null>(null);
  const [empSessions, setEmpSessions] = useState<EmployeeSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<EmployeeSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailsLoading, setIsDetailsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Account Management tab state ──
  const [accounts, setAccounts] = useState<AccountUser[]>([]);
  const [accountsLoading, setAccountsLoading] = useState(false);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);

  // ── Show toast helper ──
  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 3500);
  };

  // ── Employee details ──
  const handleSelectEmployee = useCallback(async (emp: Employee, skipPushState: boolean = false) => {
    setSelectedEmp(emp);
    setSelectedSession(null);
    setIsDetailsLoading(true);
    setEmpStats(null);
    setEmpSessions([]);

    if (!skipPushState) {
      const newPath = `/admin/employees/${emp.id}`;
      if (window.location.pathname !== newPath) {
        window.history.pushState({ mode: 'admin', activeTab: 'performance', employeeId: emp.id }, '', newPath);
      }
    }

    try {
      const [statsRes, sessionsRes] = await Promise.all([
        fetch(`/api/admin/employees/${emp.id}/stats`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`/api/admin/employees/${emp.id}/sessions`, { headers: { 'Authorization': `Bearer ${token}` } }),
      ]);
      setEmpStats(statsRes.ok ? await statsRes.json() : null);
      const sessionsData = sessionsRes.ok ? await sessionsRes.json() : null;
      setEmpSessions(sessionsData?.sessions || []);
    } catch (err) {
      console.error('Failed to load employee details:', err);
    } finally {
      setIsDetailsLoading(false);
    }
  }, [token]);

  // Sync tab and employee detail with URL on browser back/forward navigation
  useEffect(() => {
    const handleLocationChange = () => {
      const path = window.location.pathname;
      if (path === '/admin/accounts') {
        setActiveTab('accounts');
      } else if (path.startsWith('/admin/employees')) {
        setActiveTab('performance');
        
        // Handle back/forward of employee selection
        const match = path.match(/^\/admin\/employees\/([^\/]+)$/);
        if (match && match[1]) {
          const empId = match[1];
          const found = employees.find((e: Employee) => e.id === empId);
          if (found) {
            handleSelectEmployee(found, true);
          }
        } else {
          // If no ID is present, close the detail panel
          setSelectedEmp(null);
          setSelectedSession(null);
        }
      }
    };
    window.addEventListener('popstate', handleLocationChange);
    
    // Ensure URL is correct on mount
    const currentPath = window.location.pathname;
    const hasEmployeeIdInUrl = currentPath.match(/^\/admin\/employees\/([^\/]+)$/);
    
    let expectedPath = activeTab === 'accounts' ? '/admin/accounts' : '/admin/employees';
    if (selectedEmp) {
      expectedPath = `/admin/employees/${selectedEmp.id}`;
    }
    
    // Only overwrite if we are not in the process of initial loading of an employee ID from URL
    const isInitialLoadingId = hasEmployeeIdInUrl && !selectedEmp && employees.length === 0;
    
    if (!isInitialLoadingId && currentPath !== expectedPath && currentPath.startsWith('/admin')) {
      window.history.replaceState({ mode: 'admin', activeTab }, '', expectedPath);
    }

    return () => window.removeEventListener('popstate', handleLocationChange);
  }, [activeTab, selectedEmp, employees, handleSelectEmployee]);

  // ── Fetch employees performance ──
  const fetchEmployees = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/admin/employees', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Không thể tải danh sách nhân viên');
      const data = await response.json();
      const empList = data.employees || [];
      setEmployees(empList);

      // Auto-select employee from URL on mount
      const path = window.location.pathname;
      const match = path.match(/^\/admin\/employees\/([^\/]+)$/);
      if (match && match[1]) {
        const empId = match[1];
        const found = empList.find((e: Employee) => e.id === empId);
        if (found) {
          handleSelectEmployee(found, true);
        }
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [token, handleSelectEmployee]);

  // ── Fetch all accounts ──
  const fetchAccounts = useCallback(async () => {
    setAccountsLoading(true);
    setAccountsError(null);
    try {
      const response = await fetch('/api/admin/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Không thể tải danh sách tài khoản');
      const data = await response.json();
      setAccounts(data.users || []);
    } catch (err: any) {
      setAccountsError(err.message);
    } finally {
      setAccountsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  useEffect(() => {
    if (activeTab === 'accounts') fetchAccounts();
  }, [activeTab, fetchAccounts]);

  // ── Toggle activation ──
  const handleToggleStatus = async (acc: AccountUser) => {
    setUpdatingUserId(acc.id);
    try {
      const res = await fetch(`/api/admin/users/${acc.id}/status`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !acc.is_active }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Lỗi cập nhật trạng thái');
      showToast(data.message);
      setAccounts(prev => prev.map(u => u.id === acc.id ? { ...u, is_active: !u.is_active } : u));
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setUpdatingUserId(null);
    }
  };

  // ── Change role ──
  const handleChangeRole = async (acc: AccountUser, newRoleId: string) => {
    if (newRoleId === acc.role_id) return;
    setUpdatingUserId(acc.id);
    try {
      const res = await fetch(`/api/admin/users/${acc.id}/role`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ role_id: newRoleId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Lỗi cập nhật vai trò');
      showToast(data.message);
      setAccounts(prev => prev.map(u => u.id === acc.id ? { ...u, role_id: newRoleId } : u));
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setUpdatingUserId(null);
    }
  };

  return {
    token,
    logout,
    user,
    activeTab,
    handleSetActiveTab,
    employees,
    selectedEmp,
    setSelectedEmp,
    empStats,
    empSessions,
    selectedSession,
    setSelectedSession,
    isLoading,
    isDetailsLoading,
    error,
    accounts,
    accountsLoading,
    accountsError,
    toastMessage,
    updatingUserId,
    handleSelectEmployee,
    fetchEmployees,
    fetchAccounts,
    handleToggleStatus,
    handleChangeRole,
    showToast,
  };
}
