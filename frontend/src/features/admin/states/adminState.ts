export type AdminTab = 'performance' | 'accounts' | 'metrics';
export type ToastMessage = { text: string; type: 'success' | 'error' };

export function getInitialAdminTab(pathname: string, savedTab: string | null): AdminTab {
  if (pathname === '/admin/accounts') return 'accounts';
  if (pathname === '/admin/metrics') return 'metrics';
  if (pathname === '/admin/employees') return 'performance';
  if (savedTab === 'accounts' || savedTab === 'metrics') return savedTab;
  return 'performance';
}

export function getAdminPathForTab(tab: AdminTab): string {
  if (tab === 'accounts') return '/admin/accounts';
  if (tab === 'metrics') return '/admin/metrics';
  return '/admin/employees';
}

export function getEmployeeAdminPath(employeeId: string): string {
  return `/admin/employees/${employeeId}`;
}

export function getEmployeeIdFromAdminPath(pathname: string): string | null {
  const match = pathname.match(/^\/admin\/employees\/([^\/]+)$/);
  return match && match[1] ? match[1] : null;
}

export function getExpectedAdminPath(tab: AdminTab, selectedEmployeeId?: string): string {
  if (selectedEmployeeId) return getEmployeeAdminPath(selectedEmployeeId);
  return getAdminPathForTab(tab);
}
