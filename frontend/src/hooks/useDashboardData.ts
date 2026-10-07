import { useAsync } from './useAsync';
import { load } from '@/services/data';
import { dashboardFor } from '@/services/mocks/dashboard.mock';
import type { DashboardData, DashboardRange } from '@/types/dashboard';
const path = (r: DashboardRange) => `/api/dashboard?range=${r.preset}${r.preset === 'custom' ? `&from=${r.from}&to=${r.to}` : ''}`;
export const useDashboardData = (r: DashboardRange) => useAsync(() => load<DashboardData>(path(r), dashboardFor(r)), [r.preset, r.from, r.to]);
