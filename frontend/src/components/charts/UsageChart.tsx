import { ChartCard } from './ChartCard';
export const UsageChart = ({ data }: { data: object[] }) => <ChartCard title="Token usage over time" data={data} x="day" y="tokens" kind="line" />;
