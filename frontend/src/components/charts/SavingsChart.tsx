import { ChartCard } from './ChartCard';
export const SavingsChart = ({ data }: { data: object[] }) => <ChartCard title="Savings over time" data={data} x="day" y="saved" kind="line" />;
