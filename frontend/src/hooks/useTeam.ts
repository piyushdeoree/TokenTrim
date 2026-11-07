import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { Member } from '@/types/team';
export const useTeam = () => useAsync(() => load<Member[]>('/api/team'));
