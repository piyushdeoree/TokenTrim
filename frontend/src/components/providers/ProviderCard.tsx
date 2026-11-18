import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ProviderConnectionModal } from './ProviderConnectionModal';
import { testProviderConnection } from '@/services/byok/providerCredentialService';
import { PROVIDERS } from '@/services/byok/providerConfig';
import { IS_BYOK_DEMO_MODE, isByokAvailable } from '@/services/byok/adapter';
import { useProviders } from '@/context/ProviderContext';
import { toSafeByokMessage } from '@/services/byok/errors';
import type { ProviderDefinition } from '@/types/provider';

export function ProviderCard({ provider }: { provider: ProviderDefinition }) {
  const { connections, connect, disconnect } = useProviders();
  const connection = connections.find((item) => item.provider === provider.id);
  const connected = connection?.status === 'connected';
  const [showModal, setShowModal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onConnect = async (key: string) => {
    setBusy(true); setError(null); setMessage(null);
    try { await connect({ provider: provider.id, apiKey: key }); setMessage(IS_BYOK_DEMO_MODE ? 'Connected in demo mode. No provider was contacted.' : 'Provider connected through TokenTrim.'); }
    finally { setBusy(false); }
  };
  const onTest = async () => {
    setBusy(true); setError(null); setMessage(null);
    try { const result = await testProviderConnection(provider.id); (result.success ? setMessage : setError)(result.message); }
    catch (e) { setError(toSafeByokMessage(e, 'Connection test failed.')); }
    finally { setBusy(false); }
  };
  const onDisconnect = async () => {
    if (!window.confirm(`Disconnect ${provider.name}?`)) return;
    setBusy(true); setError(null); setMessage(null);
    try { await disconnect(provider.id); setMessage('Provider disconnected.'); }
    catch (e) { setError(toSafeByokMessage(e, 'Unable to disconnect provider.')); }
    finally { setBusy(false); }
  };
  return <>
    <Card className="flex h-full flex-col">
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-surface text-lg font-bold">{provider.icon}</span>
        <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold">{provider.name}</h2><Badge tone={connected ? 'good' : 'neutral'}>{connected ? 'Connected' : 'Disconnected'}</Badge></div><p className="mt-1 text-sm opacity-75">{provider.description}</p></div>
      </div>
      <div className="mt-4 min-h-10 text-sm">
        {connected && <p className="font-mono text-xs">Key: {connection?.maskedKey ?? 'Masked by service'}</p>}
        {message && <p role="status" className="mt-1 text-teal-800 dark:text-teal-300">{message}</p>}
        {error && <p role="alert" className="mt-1 text-red-700 dark:text-red-400">{error}</p>}
      </div>
      <div className="mt-auto flex flex-wrap gap-2 pt-3">
        {!connected ? <Button onClick={() => { setError(null); setShowModal(true); }} disabled={!isByokAvailable()} title={!isByokAvailable() ? 'Backend integration is not configured.' : undefined}>Connect</Button> : <>
          <Button onClick={onTest} loading={busy} disabled={busy}>Test connection</Button>
          <Button variant="ghost" onClick={() => { setError(null); setShowModal(true); }} disabled={busy}>Replace key</Button>
          <Button variant="ghost" onClick={onDisconnect} disabled={busy}>Disconnect</Button>
        </>}
      </div>
    </Card>
    {showModal && <ProviderConnectionModal provider={provider} onClose={() => setShowModal(false)} onConnect={onConnect} />}
  </>;
}

export function ProviderCards() { return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{PROVIDERS.map((provider) => <ProviderCard key={provider.id} provider={provider} />)}</div>; }
