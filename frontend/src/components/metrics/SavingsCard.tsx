import { MetricCard } from './MetricCard';
import { fmtCurrency } from '@/utils/format';
export const SavingsCard = (p: { label: string; value: number; hint?: string }) => <MetricCard {...p} value={fmtCurrency(p.value)} tone="good" />;
