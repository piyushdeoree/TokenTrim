import { useState } from 'react';
import { AsyncView } from '@/components/states/AsyncView';
import { TokenCard } from '@/components/metrics/TokenCard';
import { CostCard } from '@/components/metrics/CostCard';
import { SavingsCard } from '@/components/metrics/SavingsCard';
import { MetricCard } from '@/components/metrics/MetricCard';
import { ChartFilter } from '@/components/charts/ChartFilter';
import { UsageChart } from '@/components/charts/UsageChart';
import { CostChart } from '@/components/charts/CostChart';
import { CostByModelChart } from '@/components/charts/CostByModelChart';
import { TokenUsageByModelChart } from '@/components/charts/TokenUsageByModelChart';
import { ProjectUsageChart } from '@/components/charts/ProjectUsageChart';
import { SavingsChart } from '@/components/charts/SavingsChart';
import { useDashboardData } from '@/hooks/useDashboardData';
import { fmtPercent } from '@/utils/format';
import type { DashboardRange } from '@/types/dashboard';
export default function Dashboard() {
  const [range, setRange] = useState<DashboardRange>({ preset: 'weekly' });
  const { state, reload } = useDashboardData(range);
  return (
    <main className="mx-auto max-w-7xl space-y-6 p-4 lg:p-8">
      <div className="flex flex-wrap items-end justify-between gap-4"><h1 className="text-xl font-semibold">Dashboard</h1><ChartFilter value={range} onChange={setRange} /></div>
      <AsyncView state={state} reload={reload} isEmpty={(d) => d.totals.prompts === 0} empty={{ title: 'No analyses yet', body: 'Analyze a prompt in Token Trim and save it to see usage here.' }}>
        {(d) => (<>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
            <TokenCard label="Total tokens" value={d.totals.tokens} />
            <CostCard label="Estimated cost" value={d.totals.cost} />
            <TokenCard label="Prompts analyzed" value={d.totals.prompts} />
            <TokenCard label="Tokens saved" value={d.totals.saved} tone="good" />
            <SavingsCard label="Potential savings" value={d.totals.potential} />
            <MetricCard label="Avg. reduction" value={fmtPercent(d.totals.avg_reduction)} tone="good" />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <UsageChart data={d.usage} /><CostChart data={d.usage} /><CostByModelChart data={d.byModel} />
            <TokenUsageByModelChart data={d.byModelTokens} /><ProjectUsageChart data={d.byProject} /><SavingsChart data={d.usage} />
          </div>
        </>)}
      </AsyncView>
    </main>
  );
}
