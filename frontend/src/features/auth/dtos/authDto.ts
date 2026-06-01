import type { LoginResponse } from '../types/auth';

export function buildLoginPayload(email: string, password: string): { email: string; password: string } {
  return { email, password };
}

export function buildRegisterPayload(username: string, email: string, password: string, roleId = 'employee'): { username: string; email: string; password: string; role_id: string } {
  return { username, email, password, role_id: roleId };
}

export function parseLoginResponse(data: any): LoginResponse {
  return { access_token: data.access_token };
}

// Helper to format/translate Pydantic/FastAPI validation or system errors
export function parseDetailError(detail: any, defaultMsg: string): string {
  if (!detail) return defaultMsg;

  if (typeof detail === 'string') {
    if (detail === 'Incorrect email or password') return 'Mật khẩu hoặc email không chính xác!';
    if (detail === 'User is not active') return 'Tài khoản chưa được kích hoạt bởi Ban quản trị!';
    if (detail === 'Email already registered') return 'Địa chỉ email đã tồn tại trong hệ thống!';
    if (detail === 'Username already registered') return 'Tên tài khoản đã tồn tại trong hệ thống!';
    return detail;
  }

  if (Array.isArray(detail)) {
    const err = detail[0];
    if (err && typeof err === 'object') {
      const msg = err.msg || '';
      if (msg.includes('value is not a valid email address')) {
        return 'Địa chỉ email không đúng định dạng!';
      }
      return err.msg || JSON.stringify(err);
    }
    return detail.map(d => typeof d === 'object' ? JSON.stringify(d) : String(d)).join(', ');
  }

  if (typeof detail === 'object') {
    return detail.message || JSON.stringify(detail);
  }

  return String(detail);
}
