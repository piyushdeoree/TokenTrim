import { GroupedList } from './GroupedList';
import type { RecentItem } from '@/types/dashboard';
export const RecentActivity = ({ rows }: { rows: RecentItem[] }) =>
  <GroupedList items={rows.map((r) => ({ id: r.id, label: r.title, sub: `${r.project} · ${r.saved} tokens saved`, date: r.date }))} />;
