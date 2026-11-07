import { Card } from '@/components/ui/Card';
import { MetricCard } from '@/components/metrics/MetricCard';
import { TokenCard } from '@/components/metrics/TokenCard';
import { CostCard } from '@/components/metrics/CostCard';
import { SavingsCard } from '@/components/metrics/SavingsCard';
import { IssueList } from './IssueList';
import { SuggestionList } from './SuggestionList';
import { OptimizedPrompt } from './OptimizedPrompt';
import { fmtPercent, fmtTokens } from '@/utils/format';
import type { AnalyzePromptResponse } from '@/types/analysis';
export function AnalysisResult({ data, original, onSave }: { data: AnalyzePromptResponse; original: string; onSave?: () => void }) {
  return (
    <div className="space-y-4">
      <p role="status" className="text-sm font-medium text-teal-800 dark:text-teal-300">Analysis completed.</p>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <TokenCard label="Original tokens" value={data.original_tokens} />
        <TokenCard label="Optimized tokens" value={data.optimized_tokens} />
        <TokenCard label="Tokens saved" value={data.tokens_saved} tone="good" />
        <MetricCard label="Reduction" value={fmtPercent(data.reduction_percentage)} tone="good" />
        <CostCard label="Estimated cost" value={data.estimated_cost} hint={`~${fmtTokens(data.predicted_output_tokens)} output tokens`} />
        <SavingsCard label="Potential saving" value={data.potential_saving} />
      </div>
      <Card title="Detected issues"><IssueList issues={data.issues} /></Card>
      <Card title="Optimization suggestions"><SuggestionList items={data.suggestions} /></Card>
      <Card title="Optimized prompt"><OptimizedPrompt original={original} optimized={data.optimized_prompt} onSave={onSave} /></Card>
    </div>
  );
}
