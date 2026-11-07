import { ChartCard } from './ChartCard';
export const TokenUsageByModelChart = ({ data }: { data: object[] }) => <ChartCard title="Token usage by model API" data={data} x="name" y="tokens" kind="bar" />;
