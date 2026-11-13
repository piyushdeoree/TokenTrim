export type Role = 'owner' | 'admin' | 'member';
export interface Member { id?: number; user_id: number; full_name: string; email: string; role: Role; joined_at: string }
