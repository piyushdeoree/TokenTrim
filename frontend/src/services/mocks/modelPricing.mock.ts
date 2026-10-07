import type { ModelPricing } from '@/types/model';
// Assumed shape: confirm with Person 3.
export const pricingMock: ModelPricing[] = [
  { model: 'gpt-4o', provider: 'OpenAI', input: 2.5, output: 10, context: 128000 },
  { model: 'gpt-4o-mini', provider: 'OpenAI', input: 0.15, output: 0.6, context: 128000 },
  { model: 'claude-sonnet', provider: 'Anthropic', input: 3, output: 15, context: 200000 },
  { model: 'gemini-1.5-pro', provider: 'Google', input: 1.25, output: 5, context: 2000000 },
];
