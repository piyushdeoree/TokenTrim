import type { DashboardData, DashboardRange, UsagePoint } from '@/types/dashboard';
// Assumed shape for GET /api/dashboard?range=...&from=...&to=... (confirm with Person 3).
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
function labels(r: DashboardRange): string[] {
  if (r.preset === 'yearly') return MONTHS;
  if (r.preset === 'monthly') return Array.from({ length: 30 }, (_, i) => String(i + 1));
  if (r.preset === 'custom' && r.from && r.to && r.from <= r.to) {
    const out: string[] = []; const d = new Date(r.from); const end = new Date(r.to);
    while (d <= end && out.length < 62) { out.push(d.toISOString().slice(5, 10)); d.setUTCDate(d.getUTCDate() + 1); }
    return out;
  }
  return DAYS;
}
export function dashboardFor(r: DashboardRange): DashboardData {
  const base = r.preset === 'yearly' ? 600000 : r.preset === 'monthly' ? 28000 : 24000;
  const usage: UsagePoint[] = labels(r).map((day, i) => {
    const tokens = Math.round(base * (0.7 + 0.3 * Math.sin(i * 1.3 + 1) + 0.15 * Math.cos(i)));
    return { day, tokens, cost: +(tokens * 0.0000697).toFixed(2), saved: Math.round(tokens * 0.28) };
  });
  const tokens = usage.reduce((s, u) => s + u.tokens, 0); const cost = +usage.reduce((s, u) => s + u.cost, 0).toFixed(2); const saved = usage.reduce((s, u) => s + u.saved, 0);
  const split = (names: string[], w: number[], total: number, key: 'cost' | 'tokens') => names.map((name, i) => ({ name, [key]: +(total * w[i]).toFixed(2) }));
  const models = ['gpt-4o', 'claude-sonnet', 'gpt-4o-mini', 'gemini-1.5-pro']; const mw = [0.42, 0.31, 0.1, 0.17];
  return {
    totals: { tokens, cost, prompts: Math.round(tokens / 540), saved, potential: +(cost * 0.28).toFixed(2), avg_reduction: 28.1 },
    usage,
    byModel: split(models, mw, cost, 'cost') as DashboardData['byModel'],
    byModelTokens: split(models, mw, tokens, 'tokens').map((m) => ({ ...m, tokens: Math.round((m as { tokens: number }).tokens) })) as DashboardData['byModelTokens'],
    byProject: split(['Support bot', 'Docs summarizer', 'Internal tools'], [0.49, 0.33, 0.18], tokens, 'tokens').map((m) => ({ ...m, tokens: Math.round((m as { tokens: number }).tokens) })) as DashboardData['byProject'],
  };
}
