import { ChartCard } from './ChartCard';
import type { CurrencyCode } from '@/context/CurrencyContext';
export const CostByModelChart = ({ data, currency }: { data: object[]; currency: CurrencyCode }) => <ChartCard title="Cost by model" data={data} x="name" y="cost" kind="bar" currency={currency} />;
