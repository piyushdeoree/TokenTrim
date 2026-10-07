export type Role = 'Owner' | 'Admin' | 'Member';
export interface Member { id: string; name: string; email: string; role: Role }
