import { MetricCard } from './MetricCard';
import { fmtCurrency } from '@/utils/format';
export const CostCard = (p: { label: string; value: number; hint?: string }) => <MetricCard {...p} value={fmtCurrency(p.value)} />;
