import axios from 'axios';
import { apiClient } from './apiClient';

export interface AuthUser {
  name: string;
  email: string;
}

export interface AuthResult {
  access_token: string;
  user: AuthUser;
}

type AuthResponse = {
  access_token?: string;
  user?: AuthUser;
  full_name?: string;
};

async function call(path: string, body: Record<string, string>): Promise<AuthResult> {
  const { data } = await apiClient.post<AuthResponse>(path, body);
  if (!data.access_token) {
    throw new Error('The login response did not include an access token.');
  }
  return {
    access_token: data.access_token,
    user: data.user ?? {
      name: data.full_name ?? body.full_name ?? body.email.split('@')[0],
      email: body.email
    }
  };
}

export const login = async (email: string, password: string) => {
  const result = await call('/auth/login', { email, password });
  const { data } = await apiClient.get<{full_name:string; email:string}>('/auth/me', {
    headers: { Authorization: `Bearer ${result.access_token}` }
  });
  return { ...result, user: { name: data.full_name, email: data.email } };
};

export const register = async (name: string, email: string, password: string) => {
  await apiClient.post('/auth/register', { full_name: name, email, password });
  return login(email, password);
};

export function authErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as {
      detail?: unknown;
      error?: { message?: unknown };
    } | undefined;
    if (typeof data?.error?.message === 'string') return data.error.message;
    if (typeof data?.detail === 'string') return data.detail;
  }
  return fallback;
}
