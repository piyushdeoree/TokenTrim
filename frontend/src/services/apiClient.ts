import axios from 'axios';
export const apiClient = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_BASE_URL, timeout: 30000 });
apiClient.interceptors.request.use((c) => {
  const t = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});
apiClient.interceptors.response.use((r) => r, (e) => {
  const requestUrl = axios.isAxiosError(e) ? e.config?.url ?? '' : '';
  const isAuthRequest = requestUrl.startsWith('/auth/');
  if (axios.isAxiosError(e) && e.response?.status === 401 && !isAuthRequest
      && typeof window !== 'undefined' && window.location.pathname !== '/login') {
    localStorage.removeItem('token'); window.location.href = '/login';
  }
  return Promise.reject(e);
});
export const toMessage = (e: unknown) =>
  axios.isAxiosError(e) && e.response?.data?.detail ? String(e.response.data.detail) : 'Unable to analyze prompt. Please try again.';
