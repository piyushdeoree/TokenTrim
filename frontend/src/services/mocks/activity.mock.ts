import type { RecentItem } from '@/types/dashboard';
// Assumed endpoint: GET /api/recent-activity (confirm with Person 3). Dates are relative so grouping looks right.
export const ago = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); };
export const activityMock: RecentItem[] = [
  { id: 1, title: 'Summarize quarterly report', project: 'Docs summarizer', saved: 160, date: ago(0) },
  { id: 2, title: 'Ticket triage prompt', project: 'Support bot', saved: 90, date: ago(0) },
  { id: 3, title: 'Customer email reply', project: 'Support bot', saved: 120, date: ago(1) },
  { id: 4, title: 'Code review helper', project: 'Internal tools', saved: 75, date: ago(4) },
  { id: 5, title: 'Release notes writer', project: 'Docs summarizer', saved: 60, date: ago(12) },
];
