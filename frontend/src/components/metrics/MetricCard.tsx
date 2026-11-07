export function MetricCard({ label, value, hint, tone = 'default' }:
  { label: string; value: string; hint?: string; tone?: 'default' | 'good' }) {
  return (
    <div className="rounded-lg border border-white/10 bg-chart p-4 text-white">
      <p className="text-sm text-white/80">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone === 'good' ? 'text-btn' : 'text-white'}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-white/70">{hint}</p>}
    </div>
  );
}
