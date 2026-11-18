import type { PromptExecutionRequest, PromptExecutionResult } from '@/types/execution';
import { getByokAdapter } from './adapter';
import { sanitizeExecutionResult } from './executionUsageService';

export async function executeOptimizedPrompt(request: PromptExecutionRequest): Promise<PromptExecutionResult> {
  const result: unknown = await getByokAdapter().executePrompt(request);
  return sanitizeExecutionResult(result);
}
