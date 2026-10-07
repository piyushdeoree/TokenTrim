export interface UsagePoint { day: string; tokens: number; cost: number; saved: number }
export interface RecentItem { id: number; title: string; project: string; saved: number; date: string }
export type RangePreset = 'weekly' | 'monthly' | 'yearly' | 'custom';
export interface DashboardRange { preset: RangePreset; from?: string; to?: string }
export interface DashboardData {
  totals: { tokens: number; cost: number; prompts: number; saved: number; potential: number; avg_reduction: number };
  usage: UsagePoint[]; byModel: { name: string; cost: number }[]; byModelTokens: { name: string; tokens: number }[]; byProject: { name: string; tokens: number }[];
}
