import { useAsync } from './useAsync';
import { load } from '@/services/data';
import { activityMock } from '@/services/mocks/activity.mock';
import type { RecentItem } from '@/types/dashboard';
export const useActivity = () => useAsync(() => load<RecentItem[]>('/api/recent-activity', activityMock));
