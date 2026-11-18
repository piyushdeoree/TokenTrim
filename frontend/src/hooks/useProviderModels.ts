import { useEffect, useState } from 'react';
import type { ProviderId, ProviderModel } from '@/types/provider';
import { listProviderModels } from '@/services/byok/providerModelService';
import { toSafeByokMessage } from '@/services/byok/errors';

export function useProviderModels(provider: ProviderId | null, connected: boolean) {
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    if (!provider || !connected) { setModels([]); setLoading(false); setError(null); return; }
    setModels([]); setLoading(true); setError(null);
    listProviderModels(provider).then((items) => { if (active) setModels(items); })
      .catch((e: unknown) => { if (active) setError(toSafeByokMessage(e, 'Unable to load models.')); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [provider, connected, version]);
  return { models, loading, error, retry: () => setVersion((current) => current + 1) };
}
