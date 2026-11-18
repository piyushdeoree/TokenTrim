import type { ExecutionCost, ExecutionUsage, PromptExecutionResult } from '@/types/execution';
import { redactKnownCredentials } from './errors';

// Normalize absent backend usage without substituting misleading zero values.
export const readExecutionUsage = (usage?: ExecutionUsage | null): ExecutionUsage => usage ?? {};
export const readExecutionCost = (cost?: ExecutionCost | null): ExecutionCost => cost ?? {};

export function sanitizeExecutionResult(input: unknown): PromptExecutionResult {
  if (!input || typeof input !== 'object') throw new Error('Execution service returned an invalid result.');
  const value = input as Record<string, unknown>;
  const providers = ['openai', 'gemini', 'anthropic'];
  if (!providers.includes(String(value.provider)) || typeof value.model !== 'string' || typeof value.response !== 'string') {
    throw new Error('Execution service returned an invalid result.');
  }
  const usage = value.usage && typeof value.usage === 'object' ? value.usage as Record<string, unknown> : {};
  const cost = value.actualCost && typeof value.actualCost === 'object' ? value.actualCost as Record<string, unknown> : {};
  const savings = value.actualSavings && typeof value.actualSavings === 'object' ? value.actualSavings as Record<string, unknown> : {};
  const token = (n: unknown) => typeof n === 'number' && Number.isFinite(n) && n >= 0 ? n : null;
  const money = (obj: Record<string, unknown>): ExecutionCost => ({
    amount: typeof obj.amount === 'number' && Number.isFinite(obj.amount) ? obj.amount : null,
    currency: typeof obj.currency === 'string' && /^[A-Za-z]{3}$/.test(obj.currency) ? obj.currency.toUpperCase() : null,
  });
  const duration = typeof value.durationMs === 'number' && Number.isFinite(value.durationMs) && value.durationMs >= 0 ? value.durationMs : null;
  return {
    id: typeof value.id === 'string' ? redactKnownCredentials(value.id) : '',
    provider: value.provider as PromptExecutionResult['provider'],
    model: redactKnownCredentials(value.model),
    response: redactKnownCredentials(value.response),
    usage: { inputTokens: token(usage.inputTokens), outputTokens: token(usage.outputTokens), totalTokens: token(usage.totalTokens) },
    actualCost: money(cost),
    actualSavings: value.actualSavings == null ? null : money(savings),
    durationMs: duration,
    isDemo: value.isDemo === true,
    createdAt: typeof value.createdAt === 'string' && Number.isFinite(Date.parse(value.createdAt)) ? value.createdAt : null,
  };
}
