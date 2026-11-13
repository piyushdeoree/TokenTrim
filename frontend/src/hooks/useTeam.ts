import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { Member } from '@/types/team';
export const useTeam = (teamId: number | null) => useAsync(async () => {
  if (teamId === null) return [];
  return (await load<Member[]>(`/teams/${teamId}/members`)).map((m) => ({ ...m, id: m.user_id } as Member & {id:number}));
}, [teamId]);
