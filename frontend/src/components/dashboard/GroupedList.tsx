import { groupByDate } from '@/utils/groupByDate';
export interface ListItem { id: number | string; label: string; sub?: string; date: string }
export function GroupedList({ items }: { items: ListItem[] }) {
  if (!items.length) return <p className="px-2 text-xs opacity-70">Nothing here yet.</p>;
  return (
    <div className="space-y-3">
      {groupByDate(items).map((g) => (
        <div key={g.label}>
          <h4 className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide opacity-70">{g.label}</h4>
          <ul>{g.items.map((it) => (
            <li key={it.id} title={it.label} className="rounded-md px-2 py-1.5 hover:bg-black/10 dark:hover:bg-white/10">
              <p className="truncate text-sm">{it.label}</p>{it.sub && <p className="truncate text-xs opacity-70">{it.sub}</p>}
            </li>))}</ul>
        </div>))}
    </div>
  );
}
