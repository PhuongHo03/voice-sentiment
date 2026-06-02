import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../auth/states/AuthContext';
import {
  fetchAccountsRequest,
  fetchEmployeeDetails,
  fetchEmployeesRequest,
  updateUserRoleRequest,
  updateUserStatusRequest,
} from '../api/adminApi';
import {
  getAdminPathForTab,
  getEmployeeAdminPath,
  getEmployeeIdFromAdminPath,
  getExpectedAdminPath,
  getInitialAdminTab,
  type AdminTab,
  type ToastMessage,
} from '../states/adminState';
import type { Employee, EmployeeStats, EmployeeSession, AccountUser } from '../types/admin';

export function useAdminDashboard() {
  const { token, logout, user } = useAuth();

  const [activeTab, setActiveTab] = useState<AdminTab>(() => (
    getInitialAdminTab(window.location.pathname, localStorage.getItem('admin_active_tab'))
  ));

  const handleSetActiveTab = (tab: AdminTab) => {
    setActiveTab(tab);
    localStorage.setItem('admin_active_tab', tab);
    const newPath = getAdminPathForTab(tab);
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
  const [toastMessage, setToastMessage] = useState<ToastMessage | null>(null);
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
      const newPath = getEmployeeAdminPath(emp.id);
      if (window.location.pathname !== newPath) {
        window.history.pushState({ mode: 'admin', activeTab: 'performance', employeeId: emp.id }, '', newPath);
      }
    }

    try {
      const { stats, sessions } = await fetchEmployeeDetails(token!, emp.id);
      setEmpStats(stats);
      setEmpSessions(sessions);
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
      } else if (path === '/admin/metrics') {
        setActiveTab('metrics');
      } else if (path.startsWith('/admin/employees')) {
        setActiveTab('performance');
        
        // Handle back/forward of employee selection
        const empId = getEmployeeIdFromAdminPath(path);
        if (empId) {
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
    const hasEmployeeIdInUrl = getEmployeeIdFromAdminPath(currentPath);
    const expectedPath = getExpectedAdminPath(activeTab, selectedEmp?.id);
    
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
      const empList = await fetchEmployeesRequest(token!);
      setEmployees(empList);

      // Auto-select employee from URL on mount
      const path = window.location.pathname;
      const empId = getEmployeeIdFromAdminPath(path);
      if (empId) {
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
      const users = await fetchAccountsRequest(token!);
      setAccounts(users);
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
      const data = await updateUserStatusRequest(token!, acc);
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
      const data = await updateUserRoleRequest(token!, acc, newRoleId);
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
