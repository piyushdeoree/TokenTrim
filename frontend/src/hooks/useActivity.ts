import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { RecentItem } from '@/types/dashboard';
export const useActivity = () => useAsync(() => load<RecentItem[]>('/api/dashboard/recent-activity'));
