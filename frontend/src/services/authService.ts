
import { apiClient, USE_MOCKS } from './apiClient';

export interface AuthUser {
  name: string;
  email: string;
}

export interface AuthResult {
  access_token: string;
  user: AuthUser;
}

const wait = () => new Promise((r) => setTimeout(r, 400));

export async function login(email: string, password: string): Promise<AuthResult> {
  if (USE_MOCKS) {
    await wait();
    return {
      access_token: 'mock-token',
      user: { name: email.split('@')[0], email },
    };
  }

  const d = (await apiClient.post('/auth/login', {
    email,
    password,
  })).data;

  const me = (await apiClient.get('/auth/me', { headers: { Authorization: `Bearer ${d.access_token}` } })).data;

  return {
    access_token: d.access_token,
    user: {
      name: me.full_name,
      email: me.email,
    },
  };
}

export async function register(
  name: string,
  email: string,
  password: string
): Promise<AuthResult> {
  if (USE_MOCKS) {
    await wait();
    return {
      access_token: 'mock-token',
      user: { name, email },
    };
  }

  await apiClient.post('/auth/register', {
    full_name: name,
    email,
    password,
  });

  return login(email, password);
}
