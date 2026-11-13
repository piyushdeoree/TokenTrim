import { useAsync } from './useAsync';
import { useEffect } from 'react';
import { load } from '@/services/data';
import type { DashboardData, DashboardRange } from '@/types/dashboard';
type Overview = { total_tokens: number; total_cost: number; total_prompts: number; total_savings: number; average_reduction: number };
type Daily = { date: string; tokens: number; cost: number; requests: number; saved: number };
type Model = { model: string; tokens: number; cost: number; requests: number };
type Project = { project: string; tokens: number; cost: number; requests: number };
export const useDashboardData = (r: DashboardRange) => {
const result = useAsync(async () => {
  const days = r.preset === 'monthly' ? 30 : r.preset === 'yearly' ? 365 : 7;
  const usagePath = r.preset === 'custom' && r.from && r.to
    ? `/dashboard/daily-usage?start=${encodeURIComponent(r.from)}&end=${encodeURIComponent(r.to)}`
    : `/dashboard/daily-usage?days=${days}`;
  const [totals, saved, usage, byModel, byProject] = await Promise.all([
    load<Overview>('/dashboard/overview'),
    load<{total_tokens_saved:number}>('/dashboard/token-savings'),
    load<Daily[]>(usagePath),
    load<Model[]>('/dashboard/cost-by-model'),
    load<Project[]>('/dashboard/cost-by-project'),
  ]);
  return {
    totals: { tokens: totals.total_tokens, cost: totals.total_cost, prompts: totals.total_prompts,
    saved: saved.total_tokens_saved, potential: totals.total_savings, avg_reduction: totals.average_reduction },
    usage: usage.map((x) => ({ day: x.date, tokens: x.tokens, cost: x.cost, saved: x.saved })),
    byModel: byModel.map((x) => ({ name: x.model, cost: x.cost })),
    byModelTokens: byModel.map((x) => ({ name: x.model, tokens: x.tokens })),
    byProject: byProject.map((x) => ({ name: x.project, tokens: x.tokens })),
  } as DashboardData;
}, [r.preset, r.from, r.to]);
useEffect(() => { const refresh = () => result.reload(); window.addEventListener('tokentrim:analysis-saved', refresh); return () => window.removeEventListener('tokentrim:analysis-saved', refresh); }, [result.reload]);
return result;
};
