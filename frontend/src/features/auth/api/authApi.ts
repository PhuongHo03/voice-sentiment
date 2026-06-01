import {
  buildLoginPayload,
  buildRegisterPayload,
  parseDetailError,
  parseLoginResponse,
} from '../dtos/authDto';
import type { LoginResponse, User } from '../types/auth';

export async function fetchCurrentUser(token: string): Promise<User | null> {
  const response = await fetch('/api/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) return null;
  return response.json();
}

export async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(buildLoginPayload(email, password)),
  });

  if (!response.ok) {
    const errorData = await response.json();
    const errorDetail = parseDetailError(errorData.detail, 'Incorrect email or password');
    throw new Error(errorDetail);
  }

  return parseLoginResponse(await response.json());
}

export async function registerRequest(username: string, email: string, password: string, roleId = 'employee'): Promise<void> {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(buildRegisterPayload(username, email, password, roleId)),
  });

  if (!response.ok) {
    const errorData = await response.json();
    const errorDetail = parseDetailError(errorData.detail, 'Registration failed');
    throw new Error(errorDetail);
  }
}
