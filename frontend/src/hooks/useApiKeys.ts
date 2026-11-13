import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { ApiKey } from '@/types/apiKey';
export const useApiKeys = () => useAsync(() => load<ApiKey[]>('/api-keys'));
