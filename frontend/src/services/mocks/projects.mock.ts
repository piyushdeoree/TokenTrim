import type { Project } from '@/types/project';
import { ago } from './activity.mock';
export const projectsMock: Project[] = [
  { id: '1', name: 'Support bot', prompts: 140, tokens: 90000, cost: 5.9, history: [{ title: 'Ticket triage prompt', saved: 90, date: ago(0) }, { title: 'Customer email reply', saved: 120, date: ago(1) }] },
  { id: '2', name: 'Docs summarizer', prompts: 120, tokens: 61000, cost: 4.4, history: [{ title: 'Summarize quarterly report', saved: 160, date: ago(0) }, { title: 'Release notes writer', saved: 60, date: ago(12) }] },
];
