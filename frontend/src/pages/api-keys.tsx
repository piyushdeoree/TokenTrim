import { useState } from 'react';
import { AsyncView } from '@/components/states/AsyncView';
import { Button } from '@/components/ui/Button';
import { ApiKeyTable } from '@/components/api-keys/ApiKeyTable';
import { GenerateKeyModal } from '@/components/api-keys/GenerateKeyModal';
import { useToast } from '@/components/ui/Toast';
import { useApiKeys } from '@/hooks/useApiKeys';
import { send } from '@/services/data';
export default function ApiKeys() {
  const { state, reload } = useApiKeys(); const [open, setOpen] = useState(false); const toast = useToast();
  const revoke = async (id: string) => {
    if (!window.confirm('Revoke this key? Apps using it will stop working.')) return;
    try { await send('delete', `/api/api-keys/${id}`, null, {}); toast('Key revoked.'); reload(); } catch { toast('Unable to revoke key. Please try again.'); }
  };
  return (
    <main className="mx-auto max-w-5xl space-y-4 p-4 lg:p-8">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">API keys</h1><Button onClick={() => setOpen(true)}>Generate key</Button></div>
      <AsyncView state={state} reload={reload} isEmpty={(d) => !d.length} empty={{ title: 'No API keys', body: 'Generate a key to call the API from your app.' }}>
        {(keys) => <ApiKeyTable keys={keys} onRevoke={revoke} />}
      </AsyncView>
      {open && <GenerateKeyModal onClose={() => setOpen(false)} onDone={reload} />}
    </main>
  );
}
