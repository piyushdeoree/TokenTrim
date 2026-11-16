import { GroupedList } from './GroupedList';
import type { RecentItem } from '@/types/dashboard';
export const RecentActivity = ({ rows }: { rows: RecentItem[] }) =>
  <GroupedList items={rows.map((r) => ({ id: r.id, label: r.title,
    sub: [r.provider, r.model, r.execution_status, r.project, `${r.saved} tokens saved`, new Date(r.date).toLocaleString()].filter(Boolean).join(' · '), date: r.date }))} />;
