import type { AccountUser, Employee, EmployeeSession, EmployeeStats } from '../types/admin';

export function parseEmployeesResponse(data: any): Employee[] {
  return Array.isArray(data?.employees) ? data.employees : [];
}

export function parseAccountsResponse(data: any): AccountUser[] {
  return Array.isArray(data?.users) ? data.users : [];
}

export function parseEmployeeDetailsResponse(statsData: any, sessionsData: any): { stats: EmployeeStats | null; sessions: EmployeeSession[] } {
  return {
    stats: statsData || null,
    sessions: Array.isArray(sessionsData?.sessions) ? sessionsData.sessions : [],
  };
}

export function buildUpdateUserStatusPayload(isActive: boolean): { is_active: boolean } {
  return { is_active: isActive };
}

export function buildUpdateUserRolePayload(roleId: string): { role_id: string } {
  return { role_id: roleId };
}

export function parseAdminMessageResponse(data: any): { message: string } {
  return { message: data?.message || 'Cập nhật thành công' };
}
