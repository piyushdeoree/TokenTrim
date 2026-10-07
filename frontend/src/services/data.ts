import { apiClient, USE_MOCKS } from './apiClient';
// Generic fetch: mock when NEXT_PUBLIC_USE_MOCKS=true, real endpoint otherwise.
export async function load<T>(path: string, mock: T): Promise<T> {
  if (USE_MOCKS) { await new Promise((r) => setTimeout(r, 500)); return mock; }
  return (await apiClient.get<T>(path)).data;
}
export async function send<T>(method: 'post' | 'delete', path: string, body: unknown, mock: T): Promise<T> {
  if (USE_MOCKS) { await new Promise((r) => setTimeout(r, 400)); return mock; }
  return (await apiClient.request<T>({ method, url: path, data: body })).data;
}
