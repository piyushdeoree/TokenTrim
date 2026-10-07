import type { DashboardRange, RangePreset } from '@/types/dashboard';
const PRESETS: [RangePreset, string][] = [['weekly', 'Weekly'], ['monthly', 'Monthly'], ['yearly', 'Yearly'], ['custom', 'Custom']];
const iso = (d: Date) => d.toISOString().slice(0, 10);
export function ChartFilter({ value, onChange }: { value: DashboardRange; onChange: (r: DashboardRange) => void }) {
  const pick = (p: RangePreset) => {
    if (p !== 'custom') return onChange({ preset: p });
    const to = new Date(); const from = new Date(); from.setDate(to.getDate() - 13);
    onChange({ preset: 'custom', from: iso(from), to: iso(to) }); // default: last 14 days
  };
  const invalid = value.preset === 'custom' && !!value.from && !!value.to && value.from > value.to;
  const input = 'rounded-md border border-slate-500/50 bg-card p-1.5 text-sm';
  return (
    <fieldset className="flex flex-wrap items-end gap-3">
      <legend className="sr-only">Chart date range</legend>
      <div className="flex gap-1" role="group" aria-label="Range presets">
        {PRESETS.map(([p, label]) => (
          <button key={p} type="button" aria-pressed={value.preset === p} onClick={() => pick(p)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900 dark:focus-visible:outline-btn ${value.preset === p ? 'bg-btn text-slate-900' : 'border border-slate-500/50 hover:bg-black/10 dark:hover:bg-white/10'}`}>{label}</button>))}
      </div>
      {value.preset === 'custom' && (<>
        <label className="text-sm">From <input type="date" className={input} value={value.from ?? ''} max={value.to} onChange={(e) => onChange({ ...value, from: e.target.value })} /></label>
        <label className="text-sm">To <input type="date" className={input} value={value.to ?? ''} min={value.from} onChange={(e) => onChange({ ...value, to: e.target.value })} /></label>
        {invalid && <p role="alert" className="text-sm text-red-700 dark:text-red-400">Start date must be before the end date.</p>}
      </>)}
    </fieldset>
  );
}
