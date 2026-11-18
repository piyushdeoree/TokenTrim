import type { ExecutionAdapter } from '@/types/execution';
import type { ConnectProviderRequest, ProviderConnection, ProviderId, ProviderModel } from '@/types/provider';
import { DEVELOPMENT_MODELS } from './providerConfig';

/** Local-only simulation. It never contacts a model provider or retains an API key. */
export function createDemoAdapter(): ExecutionAdapter {
  const connections = new Map<ProviderId, ProviderConnection>();
  return {
    async listProviders() { return [...connections.values()]; },
    async connectProvider({ provider, apiKey }: ConnectProviderRequest) {
      if (apiKey.toLowerCase().startsWith('invalid')) {
        throw new Error('Demo adapter rejected this key for preview. No provider was contacted.');
      }
      const connection: ProviderConnection = {
        provider,
        status: 'connected',
        connectedAt: new Date().toISOString(),
        maskedKey: `••••••••${apiKey.slice(-4)}`,
      };
      connections.set(provider, connection);
      return connection;
    },
    async disconnectProvider(provider) { connections.delete(provider); },
    async testProvider(provider) {
      return connections.has(provider)
        ? { success: true, message: 'Demo connection is ready. No provider API was contacted.' }
        : { success: false, message: 'This provider is disconnected.' };
    },
    async listModels(provider): Promise<ProviderModel[]> { return DEVELOPMENT_MODELS[provider]; },
    async executePrompt({ prompt, provider, model }) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      if (!connections.has(provider)) throw new Error('Connect this provider before running a prompt.');
      return {
        id: `demo-${Date.now()}`,
        provider,
        model,
        response: `Demo response preview\n\nYour optimized prompt was received (${prompt.length.toLocaleString()} characters). A real model response will appear here after the backend execution API is connected.`,
        usage: {},
        actualCost: {},
        durationMs: null,
        isDemo: true,
        createdAt: new Date().toISOString(),
      };
    },
  };
}
