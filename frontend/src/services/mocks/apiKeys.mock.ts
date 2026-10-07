import type { ApiKey } from '@/types/apiKey';
// Assumed shape: confirm with Person 3.
export const apiKeysMock: ApiKey[] = [
  { id: 'k1', name: 'Production', prefix: 'tt_live_8f3a', created: '2026-09-12', limit: 100000, used: 42100 },
  { id: 'k2', name: 'Staging', prefix: 'tt_test_19bc', created: '2026-09-20', limit: 20000, used: 1300 },
];
