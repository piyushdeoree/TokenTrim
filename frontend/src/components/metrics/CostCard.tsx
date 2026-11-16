import { MetricCard } from './MetricCard';
import { fmtCurrency } from '@/utils/format';
import { useCurrency } from '@/context/CurrencyContext';
export const CostCard = (p: { label: string; value: number; hint?: string }) => {
  const { currency } = useCurrency();
  return <MetricCard {...p} value={fmtCurrency(p.value, currency)} />;
};
