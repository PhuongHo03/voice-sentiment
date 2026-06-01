export interface Role {
  id: string;
  name: string;
  description?: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
  role_id: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (username: string, email: string, password: string, roleId?: string) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

export interface LoginResponse {
  access_token: string;
}
