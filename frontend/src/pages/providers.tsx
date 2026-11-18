import { ProviderCards } from '@/components/providers/ProviderCard';
import { useProviders } from '@/context/ProviderContext';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/states/States';
import { IS_BYOK_DEMO_MODE, isByokAvailable } from '@/services/byok/adapter';

export default function ProvidersPage() {
  const { loading, error, refresh } = useProviders();
  return <main className="mx-auto max-w-6xl space-y-6 p-4 lg:p-8">
    <header className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h1 className="text-2xl font-semibold">Provider connections</h1><Badge tone={IS_BYOK_DEMO_MODE ? 'warn' : isByokAvailable() ? 'good' : 'warn'}>{IS_BYOK_DEMO_MODE ? 'Demo mode' : isByokAvailable() ? 'Backend mode' : 'Backend integration pending'}</Badge></div><p className="mt-2 max-w-2xl text-sm opacity-75">{IS_BYOK_DEMO_MODE ? 'Connect a provider key for a local interface preview. Keys are never sent to OpenAI, Google, or Anthropic from this browser.' : isByokAvailable() ? 'Provider credentials are sent through the configured TokenTrim API service.' : 'Provider connections will be available when the TokenTrim backend adapter is configured.'}</p></div></header>
    {error && <div role="alert" className="rounded-md border border-red-500/40 p-3 text-sm">{error} <button className="ml-2 underline" onClick={() => void refresh()}>Retry</button></div>}
    {loading ? <LoadingState text="Loading provider connections..." /> : <ProviderCards />}
    {IS_BYOK_DEMO_MODE && <p className="text-xs opacity-60">Connection state is kept in memory for this browser session. Demo status does not verify a real API key.</p>}
  </main>;
}
