import { useAsync } from './useAsync';
import { load } from '@/services/data';
import { teamMock } from '@/services/mocks/team.mock';
import type { Member } from '@/types/team';
export const useTeam = () => useAsync(() => load<Member[]>('/api/team', teamMock));
