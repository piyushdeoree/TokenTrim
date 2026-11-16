import { ChartCard } from './ChartCard';
export const CostChart = ({ data }: { data: object[] }) => <ChartCard title="Cost over time" data={data} x="day" y="cost" kind="line" />;
