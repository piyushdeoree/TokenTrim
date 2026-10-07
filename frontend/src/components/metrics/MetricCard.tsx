export function MetricCard({ label, value, hint, tone = 'default' }:
  { label: string; value: string; hint?: string; tone?: 'default' | 'good' }) {
  return (
    <div className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
      <p className="text-sm text-slate-600 dark:text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone === 'good' ? 'text-teal-700 dark:text-teal-400' : 'text-slate-900 dark:text-slate-100'}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
