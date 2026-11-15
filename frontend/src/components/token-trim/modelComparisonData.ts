export interface ModelCostComparisonRow {
  provider: string;
  model: string;
  originalCost: number;
  optimizedCost: number;
  savings: number;
  savingsPercent: number;
}

// Illustrative USD estimates for the comparison UI only; these are not live prices.
export const illustrativeModelComparison: ModelCostComparisonRow[] = [
  {
    provider: 'OpenAI',
    model: 'GPT-4o',
    originalCost: 0.003,
    optimizedCost: 0.0018,
    savings: 0.0012,
    savingsPercent: 40,
  },
  {
    provider: 'Anthropic',
    model: 'Claude 3.5 Sonnet',
    originalCost: 0.004,
    optimizedCost: 0.0025,
    savings: 0.0015,
    savingsPercent: 37.5,
  },
  {
    provider: 'Google',
    model: 'Gemini 1.5 Pro',
    originalCost: 0.001,
    optimizedCost: 0.0006,
    savings: 0.0004,
    savingsPercent: 40,
  },
];
