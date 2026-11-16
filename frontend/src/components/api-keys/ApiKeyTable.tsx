import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/Button';
import type { ApiKey } from '@/types/apiKey';
export const ApiKeyTable = ({ keys, onRevoke }: { keys: ApiKey[]; onRevoke: (id: number) => void }) => (
  <DataTable caption="API keys" rows={keys} cols={[
    { header: 'Name', cell: (k) => k.name }, { header: 'Key', cell: (k) => `${k.prefix}••••••••` }, { header: 'Created', cell: (k) => new Date(k.created_at).toLocaleString() },
    { header: 'Last used', cell: (k) => k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'Never' },
    { header: 'Actions', cell: (k) => <Button variant="ghost" onClick={() => onRevoke(k.id)} aria-label={`Revoke ${k.name}`}>Revoke</Button> }]} />
);
