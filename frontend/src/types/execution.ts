import type { ConnectProviderRequest, ProviderConnection, ProviderId, ProviderModel } from './provider';

export interface PromptExecutionRequest {
  prompt: string;
  provider: ProviderId;
  model: string;
}

export interface ExecutionUsage {
  inputTokens?: number | null;
  outputTokens?: number | null;
  totalTokens?: number | null;
}

export interface ExecutionCost {
  amount?: number | null;
  currency?: string | null;
}

export interface PromptExecutionResult {
  id: string;
  provider: ProviderId;
  model: string;
  response: string;
  usage: ExecutionUsage;
  actualCost: ExecutionCost;
  actualSavings?: ExecutionCost | null;
  durationMs?: number | null;
  isDemo: boolean;
  createdAt?: string | null;
}

export interface ExecutionAdapter {
  listProviders(): Promise<ProviderConnection[]>;
  connectProvider(request: ConnectProviderRequest): Promise<ProviderConnection>;
  disconnectProvider(provider: ProviderId): Promise<void>;
  testProvider(provider: ProviderId): Promise<{ success: boolean; message: string }>;
  listModels(provider: ProviderId): Promise<ProviderModel[]>;
  executePrompt(request: PromptExecutionRequest): Promise<PromptExecutionResult>;
}
