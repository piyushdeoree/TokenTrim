import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ConnectProviderRequest, ProviderConnection, ProviderId } from '@/types/provider';
import { connectProvider, disconnectProvider, listProviderConnections } from '@/services/byok/providerCredentialService';
import { toSafeByokMessage } from '@/services/byok/errors';

interface ProviderContextValue {
  connections: ProviderConnection[];
  loading: boolean;
  error: string | null;
  connect: (request: ConnectProviderRequest) => Promise<void>;
  disconnect: (provider: ProviderId) => Promise<void>;
  refresh: () => Promise<void>;
}
const Context = createContext<ProviderContextValue | null>(null);

export function ProviderProvider({ children }: { children: ReactNode }) {
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true); setError(null);
    try { setConnections(await listProviderConnections()); }
    catch (e) { setError(toSafeByokMessage(e, 'Unable to load providers.')); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const connect = useCallback(async (request: ConnectProviderRequest) => {
    const connection = await connectProvider(request);
    setConnections((current) => [...current.filter((item) => item.provider !== request.provider), connection]);
  }, []);
  const disconnect = useCallback(async (provider: ProviderId) => {
    await disconnectProvider(provider);
    setConnections((current) => current.filter((item) => item.provider !== provider));
  }, []);
  const value = useMemo(() => ({ connections, loading, error, connect, disconnect, refresh }), [connections, loading, error, connect, disconnect, refresh]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useProviders() {
  const value = useContext(Context);
  if (!value) throw new Error('useProviders must be used within ProviderProvider.');
  return value;
}
