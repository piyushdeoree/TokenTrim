export type Severity = 'low' | 'medium' | 'high';
export interface Issue { type: string; severity: Severity; description: string }
// Mirrors POST /api/analyze-prompt exactly. Do not change without Person 3.
export interface AnalyzePromptRequest { prompt: string; model: string }
export interface AnalyzePromptResponse {
  original_tokens: number; optimized_tokens: number; tokens_saved: number;
  reduction_percentage: number; predicted_output_tokens: number;
  estimated_cost: number; potential_saving: number;
  issues: Issue[]; suggestions: string[]; optimized_prompt: string;
}
