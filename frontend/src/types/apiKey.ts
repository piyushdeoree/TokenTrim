export interface ApiKey { id: number; name: string; prefix: string; created_at: string; last_used_at: string | null; is_active: boolean }
export interface NewApiKey { key: string }
