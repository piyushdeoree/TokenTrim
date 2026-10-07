import { apiClient, USE_MOCKS } from './apiClient';
import { analyzePromptMock } from './mocks/analyzePrompt.mock';
import type { AnalyzePromptRequest, AnalyzePromptResponse } from '@/types/analysis';
export async function analyzePrompt(req: AnalyzePromptRequest): Promise<AnalyzePromptResponse> {
  if (USE_MOCKS) { await new Promise((r) => setTimeout(r, 900)); return analyzePromptMock; }
  return (await apiClient.post<AnalyzePromptResponse>('/api/analyze-prompt', req)).data;
}
