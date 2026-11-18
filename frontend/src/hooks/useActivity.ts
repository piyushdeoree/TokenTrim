import { useEffect } from 'react';
import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { RecentItem } from '@/types/dashboard';
type HistoryItem = { id: number; created_at: string; original_prompt: string; project: string | null; tokens_saved: number; provider?: string | null; model?: string | null; execution_status?: string | null };
export const useActivity = () => {
  const { state, reload } = useAsync(async () => (await load<HistoryItem[]>('/history?limit=10'))
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .map((x) => ({ id: x.id, title: x.original_prompt.slice(0, 48) || 'Prompt analysis', project: x.project ?? 'Unassigned', saved: x.tokens_saved,
      date: x.created_at, provider: x.provider, model: x.model, execution_status: x.execution_status } as RecentItem)));
  useEffect(() => { window.addEventListener('tokentrim:analysis-saved', reload); return () => window.removeEventListener('tokentrim:analysis-saved', reload); }, [reload]);
  return { state, reload };
};
