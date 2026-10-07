import { useAsync } from './useAsync';
import { load } from '@/services/data';
import { apiKeysMock } from '@/services/mocks/apiKeys.mock';
import type { ApiKey } from '@/types/apiKey';
export const useApiKeys = () => useAsync(() => load<ApiKey[]>('/api/api-keys', apiKeysMock));
