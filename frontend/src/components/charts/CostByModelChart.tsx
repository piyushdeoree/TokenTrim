import { ChartCard } from './ChartCard';
export const CostByModelChart = ({ data }: { data: object[] }) => <ChartCard title="Cost by model" data={data} x="name" y="cost" kind="bar" />;
