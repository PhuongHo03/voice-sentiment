import React from 'react';
import { useAdminDashboard } from '../hooks/useAdminDashboard';
import { AdminToast } from '../components/AdminToast';
import { AdminHeader } from '../components/AdminHeader';
import { AdminTabs } from '../components/AdminTabs';
import { AdminPerformanceDashboard } from '../components/AdminPerformanceDashboard';
import { AdminAccountManagement } from '../components/AdminAccountManagement';
import { AdminObservabilityDashboard } from '../components/AdminObservabilityDashboard';
import { AdminLogsDashboard } from '../components/AdminLogsDashboard';

interface AdminDashboardPageProps {
  onBackToPersonal: () => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ onBackToPersonal }) => {
  const {
    logout,
    user,
    activeTab,
    handleSetActiveTab,
    employees,
    selectedEmp,
    empStats,
    empSessions,
    selectedSession,
    selectedSessionDetail,
    isSessionDetailLoading,
    handleSelectSession,
    closeSelectedSession,
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
  } = useAdminDashboard();

  // ── KPI ──
  const totalEmployeesCount = employees.length;
  const totalEmployeeJobs = employees.reduce((sum, item) => sum + item.total_jobs, 0);
  const scoredEmployees = employees.filter(e => e.average_score !== null);
  const systemAvgScore = scoredEmployees.length
    ? (scoredEmployees.reduce((sum, item) => sum + (item.average_score || 0), 0) / scoredEmployees.length).toFixed(1)
    : 'Chưa có';

  // ── Account stats ──
  const pendingCount = accounts.filter(a => !a.is_active).length;
  const adminCount = accounts.filter(a => a.role_id === 'admin').length;

  return (
    <div className="admin-layout">
      {/* Toast Notification */}
      <AdminToast toastMessage={toastMessage} />

      {/* Top Navigation */}
      <AdminHeader username={user?.username} onBackToPersonal={onBackToPersonal} logout={logout} />

      <AdminTabs activeTab={activeTab} handleSetActiveTab={handleSetActiveTab} pendingCount={pendingCount} />

      {/* ════════════════════════════════════════════════════════════
          TAB 1: PERFORMANCE DASHBOARD
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'performance' && (
        <AdminPerformanceDashboard
          employees={employees}
          selectedEmp={selectedEmp}
          empStats={empStats}
          empSessions={empSessions}
          selectedSession={selectedSession}
          selectedSessionDetail={selectedSessionDetail}
          isSessionDetailLoading={isSessionDetailLoading}
          handleSelectSession={handleSelectSession}
          closeSelectedSession={closeSelectedSession}
          isLoading={isLoading}
          isDetailsLoading={isDetailsLoading}
          error={error}
          handleSelectEmployee={handleSelectEmployee}
          totalEmployeesCount={totalEmployeesCount}
          totalEmployeeJobs={totalEmployeeJobs}
          systemAvgScore={systemAvgScore}
          currentUserId={user?.id}
          fetchEmployees={fetchEmployees}
        />
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB 2: ACCOUNT MANAGEMENT
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'accounts' && (
        <AdminAccountManagement
          accounts={accounts}
          userId={user?.id}
          pendingCount={pendingCount}
          adminCount={adminCount}
          accountsLoading={accountsLoading}
          accountsError={accountsError}
          updatingUserId={updatingUserId}
          fetchAccounts={fetchAccounts}
          handleToggleStatus={handleToggleStatus}
          handleChangeRole={handleChangeRole}
        />
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB 3: METRICS
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'metrics' && (
        <AdminObservabilityDashboard active={activeTab === 'metrics'} />
      )}

      {/* ════════════════════════════════════════════════════════════
          TAB 4: LOGS
      ════════════════════════════════════════════════════════════ */}
      {activeTab === 'logs' && (
        <AdminLogsDashboard />
      )}
    </div>
  );
};

export default AdminDashboardPage;
