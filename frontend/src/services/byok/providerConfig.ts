import type { ProviderDefinition, ProviderId, ProviderModel } from '@/types/provider';

export const PROVIDERS: ProviderDefinition[] = [
  { id: 'openai', name: 'OpenAI', shortName: 'OpenAI', description: 'Connect an OpenAI API key to run optimized prompts.', icon: 'O' },
  { id: 'gemini', name: 'Google Gemini', shortName: 'Gemini', description: 'Connect a Google AI API key to run optimized prompts.', icon: 'G' },
  { id: 'anthropic', name: 'Anthropic Claude', shortName: 'Claude', description: 'Connect an Anthropic API key to run optimized prompts.', icon: 'A' },
];

// Development-only catalog. Replace the model service with backend discovery when available.
export const DEVELOPMENT_MODELS: Record<ProviderId, ProviderModel[]> = {
  openai: [
    { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', availability: 'demo' },
    { id: 'gpt-4o-mini', name: 'GPT-4o mini', provider: 'openai', availability: 'demo' },
  ],
  gemini: [
    { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', provider: 'gemini', availability: 'demo' },
    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'gemini', availability: 'demo' },
  ],
  anthropic: [
    { id: 'claude-3-5-sonnet-latest', name: 'Claude 3.5 Sonnet', provider: 'anthropic', availability: 'demo' },
    { id: 'claude-3-5-haiku-latest', name: 'Claude 3.5 Haiku', provider: 'anthropic', availability: 'demo' },
  ],
};
