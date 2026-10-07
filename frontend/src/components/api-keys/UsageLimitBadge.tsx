import { Badge } from '@/components/ui/Badge';
export function UsageLimitBadge({ used, limit }: { used: number; limit: number }) {
  const pct = limit ? Math.round((used / limit) * 100) : 0;
  return <Badge tone={pct >= 90 ? 'bad' : pct >= 70 ? 'warn' : 'good'}>{used.toLocaleString()} / {limit.toLocaleString()} tokens ({pct}%)</Badge>;
}
