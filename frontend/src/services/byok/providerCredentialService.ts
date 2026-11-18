import type { ConnectProviderRequest, ProviderConnection, ProviderId } from '@/types/provider';
import { getByokAdapter } from './adapter';
import { sanitizeProviderConnection, toSafeByokMessage } from './errors';

export async function listProviderConnections(): Promise<ProviderConnection[]> {
  const result: unknown = await getByokAdapter().listProviders();
  if (!Array.isArray(result)) throw new Error('Provider service returned an invalid provider list.');
  return result.map(sanitizeProviderConnection);
}
export async function connectProvider(request: ConnectProviderRequest): Promise<ProviderConnection> {
  return sanitizeProviderConnection(await getByokAdapter().connectProvider(request));
}
export const disconnectProvider = (provider: ProviderId): Promise<void> => getByokAdapter().disconnectProvider(provider);
export async function testProviderConnection(provider: ProviderId) {
  const result: unknown = await getByokAdapter().testProvider(provider);
  if (!result || typeof result !== 'object') throw new Error('Provider service returned an invalid test result.');
  const value = result as Record<string, unknown>;
  return {
    success: value.success === true,
    message: toSafeByokMessage(new Error(typeof value.message === 'string' ? value.message : ''), 'Connection test finished.'),
  };
}
