import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/Button';
import { UsageLimitBadge } from './UsageLimitBadge';
import type { ApiKey } from '@/types/apiKey';
export const ApiKeyTable = ({ keys, onRevoke }: { keys: ApiKey[]; onRevoke: (id: string) => void }) => (
  <DataTable caption="API keys" rows={keys} cols={[
    { header: 'Name', cell: (k) => k.name }, { header: 'Key', cell: (k) => `${k.prefix}••••••••` }, { header: 'Created', cell: (k) => k.created },
    { header: 'Usage', cell: (k) => <UsageLimitBadge used={k.used} limit={k.limit} /> },
    { header: 'Actions', cell: (k) => <Button variant="ghost" onClick={() => onRevoke(k.id)} aria-label={`Revoke ${k.name}`}>Revoke</Button> }]} />
);
