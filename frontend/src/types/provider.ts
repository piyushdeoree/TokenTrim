export type ProviderId = 'openai' | 'gemini' | 'anthropic';
export type ConnectionStatus = 'connected' | 'disconnected';

export interface ProviderDefinition {
  id: ProviderId;
  name: string;
  shortName: string;
  description: string;
  icon: string;
}

export interface ProviderConnection {
  provider: ProviderId;
  status: ConnectionStatus;
  connectedAt: string;
  maskedKey?: string;
}

export interface ConnectProviderRequest { provider: ProviderId; apiKey: string }
export interface TestProviderResponse { success: boolean; message: string }
export interface ProviderModel { id: string; name: string; provider: ProviderId; availability: 'demo' | 'live' }
