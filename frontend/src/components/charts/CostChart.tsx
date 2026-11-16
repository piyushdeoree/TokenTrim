import { ChartCard } from './ChartCard';
import type { CurrencyCode } from '@/context/CurrencyContext';
export const CostChart = ({ data, currency }: { data: object[]; currency: CurrencyCode }) => <ChartCard title="Cost over time" data={data} x="day" y="cost" kind="line" currency={currency} />;
