import type { Issue } from '@/types/analysis';
const tone = { low: 'bg-slate-200 text-slate-900', medium: 'bg-amber-200 text-amber-950', high: 'bg-red-200 text-red-950' };
export function IssueList({ issues }: { issues: Issue[] }) {
  if (!issues.length) return <p className="text-sm text-slate-600">No issues detected.</p>;
  return (
    <ul className="space-y-2">
      {issues.map((i, k) => (
        <li key={k} className="flex items-start gap-2 text-sm text-slate-900 dark:text-slate-100">
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${tone[i.severity]}`}>{i.severity}</span>
          <span><span className="font-medium capitalize">{i.type}:</span> {i.description}</span>
        </li>
      ))}
    </ul>
  );
}
