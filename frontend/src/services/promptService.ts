import { apiClient } from './apiClient';
import type { AnalyzePromptRequest, AnalyzePromptResponse } from '@/types/analysis';
export async function analyzePrompt(req: AnalyzePromptRequest): Promise<AnalyzePromptResponse> {
  return (await apiClient.post<AnalyzePromptResponse>('/api/analyze-prompt', req)).data;
}
