import { apiClient } from './apiClient';
export interface AuthUser { name: string; email: string }
export interface AuthResult { access_token: string; user: AuthUser }
async function call(path: string, body: Record<string, string>): Promise<AuthResult> {
  const d = (await apiClient.post(path, body)).data;
  return { access_token: d.access_token, user: d.user ?? { name: body.name ?? body.email.split('@')[0], email: body.email } };
}
export const login = (email: string, password: string) => call('/api/auth/login', { email, password });
export const register = (name: string, email: string, password: string) => call('/api/auth/register', { name, email, password });
