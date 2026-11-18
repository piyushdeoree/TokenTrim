import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PROVIDERS } from '@/services/byok/providerConfig';
import { readExecutionCost, readExecutionUsage } from '@/services/byok/executionUsageService';
import { fmtTokens } from '@/utils/format';
import { useCurrency } from '@/context/CurrencyContext';
import type { PromptExecutionResult } from '@/types/execution';

function formatMoney(amount?: number | null, currency?: string | null) {
  if (amount == null || !Number.isFinite(amount) || !currency) return 'Not available';
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency, currencyDisplay: 'code', minimumFractionDigits: 2, maximumFractionDigits: 8 }).format(amount); }
  catch { return `${amount.toFixed(8)} ${currency}`; }
}

export function ExecutionResult({ result, estimatedCost, estimatedSaving }: {
  result: PromptExecutionResult; estimatedCost?: number | null; estimatedSaving?: number | null;
}) {
  const { currency } = useCurrency();
  const provider = PROVIDERS.find((item) => item.id === result.provider)?.name ?? result.provider;
  const usage = readExecutionUsage(result.usage);
  const cost = readExecutionCost(result.actualCost);
  const tokenValue = (value?: number | null) => value == null ? 'Not available' : fmtTokens(value);
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-semibold">Execution result</h3><Badge tone={result.isDemo ? 'warn' : 'good'}>{result.isDemo ? 'Demo response · not from an LLM' : 'Completed'}</Badge></div>
    {result.isDemo && <p role="note" className="rounded-md border border-amber-500/40 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">This is a simulated preview. No provider API was called, and its usage and actual cost are unavailable.</p>}
    <Card title={`${provider} · ${result.model}`}>
      <pre aria-label="Generated response" className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words font-sans text-sm leading-6">{result.response}</pre>
    </Card>
    <Card title="Execution usage">
      <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
        <div><dt className="opacity-70">Input tokens</dt><dd className="mt-1 font-semibold">{tokenValue(usage.inputTokens)}</dd></div>
        <div><dt className="opacity-70">Output tokens</dt><dd className="mt-1 font-semibold">{tokenValue(usage.outputTokens)}</dd></div>
        <div><dt className="opacity-70">Total tokens</dt><dd className="mt-1 font-semibold">{tokenValue(usage.totalTokens)}</dd></div>
        <div><dt className="opacity-70">Actual execution cost</dt><dd className="mt-1 font-semibold">{formatMoney(cost.amount, cost.currency)}</dd></div>
        <div><dt className="opacity-70">Execution duration</dt><dd className="mt-1 font-semibold">{result.durationMs == null ? 'Not available' : `${result.durationMs.toLocaleString()} ms`}</dd></div>
        <div><dt className="opacity-70">Completed</dt><dd className="mt-1 font-semibold">{result.createdAt ? new Date(result.createdAt).toLocaleString() : 'Not available'}</dd></div>
      </dl>
    </Card>
    <Card title="Estimated and actual costs">
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div><dt className="opacity-70">Estimated optimization cost</dt><dd className="mt-1 font-semibold">{formatMoney(estimatedCost, currency)}</dd></div>
        <div><dt className="opacity-70">Actual execution cost</dt><dd className="mt-1 font-semibold">{formatMoney(cost.amount, cost.currency)}</dd></div>
        <div><dt className="opacity-70">Estimated optimization savings</dt><dd className="mt-1 font-semibold">{formatMoney(estimatedSaving, currency)}</dd></div>
        <div><dt className="opacity-70">Actual execution savings</dt><dd className="mt-1 font-semibold">{formatMoney(result.actualSavings?.amount, result.actualSavings?.currency)}</dd></div>
      </dl>
      <p className="mt-3 text-xs opacity-65">Estimated figures are from prompt optimization. Actual figures are returned by the execution service; the demo has no provider usage or cost.</p>
    </Card>
  </div>;
}
