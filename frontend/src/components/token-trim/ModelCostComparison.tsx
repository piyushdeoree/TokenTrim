import { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { fmtCurrency, fmtPercent } from '@/utils/format';
import { illustrativeModelComparison } from './modelComparisonData';

type SortBy = 'optimizedCost' | 'savingsPercent';

export function ModelCostComparison() {
  const [expanded, setExpanded] = useState(false);
  const [provider, setProvider] = useState('all');
  const [sortBy, setSortBy] = useState<SortBy>('optimizedCost');

  const rows = useMemo(() => {
    const filtered = illustrativeModelComparison.filter((row) => provider === 'all' || row.provider === provider);
    return [...filtered].sort((a, b) => sortBy === 'optimizedCost'
      ? a.optimizedCost - b.optimizedCost
      : b.savingsPercent - a.savingsPercent);
  }, [provider, sortBy]);

  const lowestCost = rows.length ? Math.min(...rows.map((row) => row.optimizedCost)) : null;
  const highestSavings = rows.length ? Math.max(...rows.map((row) => row.savings)) : null;

  return (
    <Card title="Compare Across LLMs">
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
        Compare the estimated cost of your original and optimized prompt across different AI models.
      </p>
      <Button
        aria-expanded={expanded}
        aria-controls="model-cost-comparison-details"
        onClick={() => setExpanded((value) => !value)}
      >
        {expanded ? 'Hide comparison' : 'Compare All Supported LLMs'}
      </Button>
      {expanded && (
        <div id="model-cost-comparison-details" className="mt-5 space-y-4">
          <p role="note" className="rounded-md border border-amber-500/30 bg-amber-100/70 px-3 py-2 text-sm text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
            Illustrative comparison — live model pricing is not connected yet.
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Summary label="Lowest optimized cost" value={rows.length ? fmtCurrency(lowestCost!) : '—'} detail={rows.find((row) => row.optimizedCost === lowestCost)?.model} />
            <Summary label="Highest potential savings" value={rows.length ? fmtCurrency(highestSavings!) : '—'} detail={rows.find((row) => row.savings === highestSavings)?.model} />
            <Summary label="Models compared" value={String(rows.length)} detail="Illustrative estimates" />
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <label className="block text-sm font-medium">
              Provider
              <select
                aria-label="Filter by provider"
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
                className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm dark:border-slate-600 dark:bg-slate-950 sm:min-w-44"
              >
                <option value="all">All providers</option>
                {Array.from(new Set(illustrativeModelComparison.map((row) => row.provider)).values()).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium">
              Sort by
              <select
                aria-label="Sort comparisons"
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value as SortBy)}
                className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm dark:border-slate-600 dark:bg-slate-950 sm:min-w-52"
              >
                <option value="optimizedCost">Optimized cost (lowest first)</option>
                <option value="savingsPercent">Savings % (highest first)</option>
              </select>
            </label>
          </div>

          <div className="-mx-1 overflow-x-auto rounded-md border border-black/10 dark:border-white/10">
            <table className="w-full min-w-[680px] table-fixed text-left text-sm">
              <thead className="bg-surface/40 text-xs uppercase tracking-wide text-slate-600 dark:text-slate-300">
                <tr>
                  <th scope="col" className="w-[16%] px-3 py-3">Provider</th>
                  <th scope="col" className="w-[24%] px-3 py-3">Model</th>
                  <th scope="col" className="w-[15%] px-3 py-3">Original cost</th>
                  <th scope="col" className="w-[17%] px-3 py-3">Optimized cost</th>
                  <th scope="col" className="w-[15%] px-3 py-3">Savings</th>
                  <th scope="col" className="w-[13%] px-3 py-3">Savings %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/10 dark:divide-white/10">
                {rows.map((row) => {
                  const isLowest = row.optimizedCost === lowestCost;
                  return (
                    <tr key={row.provider} className={isLowest ? 'bg-teal-100/70 dark:bg-teal-950/50' : ''}>
                      <td className="px-3 py-3 font-medium">{row.provider}</td>
                      <td className="px-3 py-3 break-words font-medium">
                        <span>{row.model}</span>
                        {isLowest && <Badge tone="good">Lowest cost</Badge>}
                      </td>
                      <td className="px-3 py-3 tabular-nums">{fmtCurrency(row.originalCost)}</td>
                      <td className="px-3 py-3 font-semibold tabular-nums">{fmtCurrency(row.optimizedCost)}</td>
                      <td className="px-3 py-3 tabular-nums">{fmtCurrency(row.savings)}</td>
                      <td className="px-3 py-3 tabular-nums">{fmtPercent(row.savingsPercent)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">All amounts are illustrative USD estimates, not actual API charges.</p>
        </div>
      )}
    </Card>
  );
}

function Summary({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="min-w-0 rounded-md border border-black/10 bg-surface/20 p-3 dark:border-white/10">
      <p className="text-xs font-medium text-slate-600 dark:text-slate-300">{label}</p>
      <p className="mt-1 break-words text-lg font-semibold tabular-nums">{value}</p>
      {detail && <p className="mt-0.5 truncate text-xs text-slate-600 dark:text-slate-400">{detail}</p>}
    </div>
  );
}
