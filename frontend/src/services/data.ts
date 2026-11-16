import { apiClient } from './apiClient';
export async function load<T>(path: string): Promise<T> {
  return (await apiClient.get<T>(path)).data;
}
export async function send<T>(method: 'post' | 'patch' | 'put' | 'delete', path: string, body?: unknown): Promise<T> {
  return (await apiClient.request<T>({ method, url: path, data: body })).data;
}
