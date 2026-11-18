import type { ProviderId, ProviderModel } from '@/types/provider';
import { getByokAdapter } from './adapter';
import { redactKnownCredentials } from './errors';

export async function listProviderModels(provider: ProviderId): Promise<ProviderModel[]> {
  const result: unknown = await getByokAdapter().listModels(provider);
  if (!Array.isArray(result)) throw new Error('Provider service returned an invalid model list.');
  return result.map((input) => {
    if (!input || typeof input !== 'object') throw new Error('Provider service returned an invalid model.');
    const value = input as Record<string, unknown>;
    if (typeof value.id !== 'string' || typeof value.name !== 'string' || value.provider !== provider) {
      throw new Error('Provider service returned an invalid model.');
    }
    return { id: redactKnownCredentials(value.id), name: redactKnownCredentials(value.name), provider, availability: value.availability === 'live' ? 'live' : 'demo' };
  });
}
