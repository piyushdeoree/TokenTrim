import { ChartCard } from './ChartCard';
export const ProjectUsageChart = ({ data }: { data: object[] }) => <ChartCard title="Usage by project" data={data} x="name" y="tokens" kind="bar" />;
