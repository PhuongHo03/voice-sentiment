import {
  buildUpdateUserRolePayload,
  buildUpdateUserStatusPayload,
  parseAccountsResponse,
  parseAdminMessageResponse,
  parseEmployeeDetailsResponse,
  parseEmployeesResponse,
} from '../dtos/adminDto';
import type { AccountUser, Employee, EmployeeSession, EmployeeStats } from '../types/admin';
import type { JobStatus } from '../../../shared/types/analysis';

function authHeaders(token: string): Record<string, string> {
  return { 'Authorization': `Bearer ${token}` };
}

export async function fetchEmployeeDetails(token: string, employeeId: string): Promise<{ stats: EmployeeStats | null; sessions: EmployeeSession[] }> {
  const [statsRes, sessionsRes] = await Promise.all([
    fetch(`/api/admin/employees/${employeeId}/stats`, { headers: authHeaders(token) }),
    fetch(`/api/admin/employees/${employeeId}/sessions`, { headers: authHeaders(token) }),
  ]);

  const stats = statsRes.ok ? await statsRes.json() : null;
  const sessionsData = sessionsRes.ok ? await sessionsRes.json() : null;

  return parseEmployeeDetailsResponse(stats, sessionsData);
}

export async function fetchEmployeeSessionDetail(token: string, employeeId: string, jobId: string): Promise<JobStatus> {
  const response = await fetch(`/api/admin/employees/${employeeId}/sessions/${jobId}`, {
    headers: authHeaders(token),
  });
  if (!response.ok) throw new Error('Không thể tải chi tiết phiên làm việc');
  return response.json();
}

export async function fetchEmployeesRequest(token: string): Promise<Employee[]> {
  const response = await fetch('/api/admin/employees', {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error('Không thể tải danh sách nhân viên');
  const data = await response.json();
  return parseEmployeesResponse(data);
}

export async function fetchAccountsRequest(token: string): Promise<AccountUser[]> {
  const response = await fetch('/api/admin/users', {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error('Không thể tải danh sách tài khoản');
  const data = await response.json();
  return parseAccountsResponse(data);
}

export async function updateUserStatusRequest(token: string, account: AccountUser): Promise<{ message: string }> {
  const res = await fetch(`/api/admin/users/${account.id}/status`, {
    method: 'PATCH',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(buildUpdateUserStatusPayload(!account.is_active)),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Lỗi cập nhật trạng thái');
  return parseAdminMessageResponse(data);
}

export async function updateUserRoleRequest(token: string, account: AccountUser, newRoleId: string): Promise<{ message: string }> {
  const res = await fetch(`/api/admin/users/${account.id}/role`, {
    method: 'PATCH',
    headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(buildUpdateUserRolePayload(newRoleId)),
  });
  const data = await res.json();
  return parseAdminMessageResponse(data);
}

export async function fetchWorkerLogsRequest(token: string, workerName: string, lines: number = 100): Promise<{ worker: string; logs: string }> {
  const response = await fetch(`/api/admin/logs/${workerName}?lines=${lines}`, {
    headers: authHeaders(token)
  });
  if (!response.ok) throw new Error('Không thể tải logs của worker');
  return await response.json();
}
