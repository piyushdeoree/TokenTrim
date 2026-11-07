import { DataTable, Col } from '@/components/ui/DataTable';
import { GroupedList } from './GroupedList';
export interface HistoryRow { id: number; project?: string; title: string; saved: number; date: string }
export function ProjectHistoryTable({ rows, showProject, compact }: { rows: HistoryRow[]; showProject?: boolean; compact?: boolean }) {
  if (!rows.length) return <p className="text-sm">No saved analyses yet.</p>;
  if (compact) return <GroupedList items={rows.map((r) => ({ id: r.id, label: r.title, sub: r.project, date: r.date }))} />;
  const cols: Col<HistoryRow>[] = [{ header: 'Prompt', cell: (r) => r.title }, { header: 'Tokens saved', cell: (r) => r.saved }, { header: 'Date', cell: (r) => r.date }];
  if (showProject) cols.unshift({ header: 'Project', cell: (r) => r.project });
  return <DataTable caption="Project history" rows={rows} cols={cols} />;
}
