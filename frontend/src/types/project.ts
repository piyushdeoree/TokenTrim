export interface HistoryItem { title: string; saved: number; date: string }
export interface Project { id: string; name: string; prompts: number; tokens: number; cost: number; history: HistoryItem[] }
