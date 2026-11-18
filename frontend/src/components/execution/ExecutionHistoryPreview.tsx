import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

type ExecutionHistoryItem = {
  id: string;
  provider: string;
  model: string;
  executedAt: string;
  status: 'succeeded' | 'failed';
  inputTokens: number | null;
  outputTokens: number | null;
  durationMs: number | null;
  actualCost: { amount: number; currency: string } | null;
};

export const DEMO_EXECUTION_HISTORY: ExecutionHistoryItem[] = [
  { id: 'demo-run-1', provider: 'OpenAI', model: 'GPT-4o mini', executedAt: '2026-11-18T10:32:00Z', status: 'succeeded', inputTokens: 184, outputTokens: 326, durationMs: 842, actualCost: { amount: 0.000081, currency: 'USD' } },
  { id: 'demo-run-2', provider: 'Google Gemini', model: 'Gemini 2.0 Flash', executedAt: '2026-11-17T15:08:00Z', status: 'succeeded', inputTokens: 92, outputTokens: 210, durationMs: 615, actualCost: { amount: 0.000014, currency: 'USD' } },
  { id: 'demo-run-3', provider: 'Anthropic Claude', model: 'Claude 3.5 Haiku', executedAt: '2026-11-16T08:41:00Z', status: 'failed', inputTokens: null, outputTokens: null, durationMs: null, actualCost: null },
];

function formatCost(cost: ExecutionHistoryItem['actualCost']) {
  if (!cost || !Number.isFinite(cost.amount)) return 'Not available';
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: cost.currency, currencyDisplay: 'code', maximumFractionDigits: 8 }).format(cost.amount);
  } catch {
    return 'Not available';
  }
}

export function ExecutionHistoryPreview({ showDemo }: { showDemo: boolean }) {
  return <section aria-labelledby="execution-history-title" className="space-y-3">
    <div className="flex flex-wrap items-center gap-2">
      <h2 id="execution-history-title" className="text-lg font-semibold">Execution history</h2>
      {showDemo && <Badge tone="warn">Demo sample data</Badge>}
    </div>
    {showDemo
      ? <><p className="text-sm opacity-70">Sample rows show the execution details available here. They are not saved runs or real provider usage.</p>
        <div className="space-y-3">{DEMO_EXECUTION_HISTORY.map((item) => <Card key={item.id}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div><h3 className="font-semibold">{item.provider} · {item.model}</h3><p className="mt-1 text-xs opacity-70">{new Date(item.executedAt).toLocaleString()}</p></div>
            <Badge tone={item.status === 'succeeded' ? 'good' : 'bad'}>{item.status === 'succeeded' ? 'Succeeded' : 'Failed'}</Badge>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div><dt className="text-xs opacity-70">Input tokens</dt><dd className="mt-1 font-semibold">{item.inputTokens == null ? 'Not available' : item.inputTokens.toLocaleString()}</dd></div>
            <div><dt className="text-xs opacity-70">Output tokens</dt><dd className="mt-1 font-semibold">{item.outputTokens == null ? 'Not available' : item.outputTokens.toLocaleString()}</dd></div>
            <div><dt className="text-xs opacity-70">Execution duration</dt><dd className="mt-1 font-semibold">{item.durationMs == null ? 'Not available' : `${item.durationMs.toLocaleString()} ms`}</dd></div>
            <div><dt className="text-xs opacity-70">Actual execution cost</dt><dd className="mt-1 font-semibold">{formatCost(item.actualCost)}</dd></div>
          </dl>
        </Card>)}</div>
      </>
      : <Card><p className="text-sm opacity-75">Execution history will appear here when available.</p></Card>}
  </section>;
}
