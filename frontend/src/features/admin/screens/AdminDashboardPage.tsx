import React from 'react';
import { useAdminDashboard } from '../hooks/useAdminDashboard';
import { AdminToast } from '../components/AdminToast';
import { AdminHeader } from '../components/AdminHeader';
import { AdminTabs } from '../components/AdminTabs';
import { AdminPerformanceDashboard } from '../components/AdminPerformanceDashboard';
import { AdminAccountManagement } from '../components/AdminAccountManagement';
import { AdminObservabilityDashboard } from '../components/AdminObservabilityDashboard';

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
    fetchAccounts,
    handleToggleStatus,
    handleChangeRole,
  } = useAdminDashboard();

  // ── SVG donut helpers ──
  const donutPos = empStats?.sentiment_distribution?.positive ?? selectedEmp?.sentiment_distribution?.positive ?? 0;
  const donutNeu = empStats?.sentiment_distribution?.neutral ?? selectedEmp?.sentiment_distribution?.neutral ?? 0;
  const donutNeg = empStats?.sentiment_distribution?.negative ?? selectedEmp?.sentiment_distribution?.negative ?? 0;
  const donutTotal = donutPos + donutNeu + donutNeg;
  const posPct = donutTotal ? (donutPos / donutTotal) * 100 : 0;
  const neuPct = donutTotal ? (donutNeu / donutTotal) * 100 : 0;
  const negPct = donutTotal ? (donutNeg / donutTotal) * 100 : 0;
  const circ = 2 * Math.PI * 38;
  const negOffset = 0;
  const neuOffset = (donutNeg / donutTotal) * circ;
  const posOffset = ((donutNeg + donutNeu) / donutTotal) * circ;

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
          setSelectedSession={setSelectedSession}
          isLoading={isLoading}
          isDetailsLoading={isDetailsLoading}
          error={error}
          handleSelectEmployee={handleSelectEmployee}
          totalEmployeesCount={totalEmployeesCount}
          totalEmployeeJobs={totalEmployeeJobs}
          systemAvgScore={systemAvgScore}
          donutPos={donutPos}
          donutNeu={donutNeu}
          donutNeg={donutNeg}
          donutTotal={donutTotal}
          posPct={posPct}
          neuPct={neuPct}
          negPct={negPct}
          circ={circ}
          negOffset={negOffset}
          neuOffset={neuOffset}
          posOffset={posOffset}
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
    </div>
  );
};

export default AdminDashboardPage;
