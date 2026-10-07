import { MetricCard } from './MetricCard';
import { fmtTokens } from '@/utils/format';
export const TokenCard = (p: { label: string; value: number; hint?: string; tone?: 'default' | 'good' }) => <MetricCard {...p} value={fmtTokens(p.value)} />;
