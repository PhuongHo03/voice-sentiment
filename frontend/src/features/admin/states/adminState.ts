export type AdminTab = 'performance' | 'accounts' | 'observability';
export type ToastMessage = { text: string; type: 'success' | 'error' };

export function getInitialAdminTab(pathname: string, savedTab: string | null): AdminTab {
  if (pathname === '/admin/accounts') return 'accounts';
  if (pathname === '/admin/observability') return 'observability';
  if (pathname === '/admin/employees') return 'performance';
  if (savedTab === 'accounts' || savedTab === 'observability') return savedTab;
  return 'performance';
}

export function getAdminPathForTab(tab: AdminTab): string {
  if (tab === 'accounts') return '/admin/accounts';
  if (tab === 'observability') return '/admin/observability';
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
