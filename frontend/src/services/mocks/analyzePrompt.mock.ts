import type { AnalyzePromptResponse } from '@/types/analysis';
export const analyzePromptMock: AnalyzePromptResponse = {
  original_tokens: 520, optimized_tokens: 360, tokens_saved: 160,
  reduction_percentage: 30.77, predicted_output_tokens: 250,
  estimated_cost: 0.012, potential_saving: 0.004,
  issues: [
    { type: 'redundancy', severity: 'medium', description: 'Repeated instruction detected' },
    { type: 'verbosity', severity: 'low', description: 'Verbose wording can be shortened' },
  ],
  suggestions: ['Remove repeated instructions', 'Replace long phrases with direct verbs'],
  optimized_prompt: 'Summarize the following document clearly.',
};
