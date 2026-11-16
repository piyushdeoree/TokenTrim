import { Button } from '@/components/ui/Button';
import { PromptComparison } from './PromptComparison';
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard';
export function OptimizedPrompt({ original, optimized, onSave }: { original: string; optimized: string; onSave?: () => void }) {
  const { copied, copy } = useCopyToClipboard();
  return (<>
    <PromptComparison original={original} optimized={optimized} />
    <div className="mt-3 flex flex-wrap gap-2">
      <Button onClick={() => copy(optimized)}>{copied ? 'Copied' : 'Copy optimized prompt'}</Button>
      {onSave && <Button variant="ghost" onClick={onSave}>Save analysis</Button>}
    </div></>);
}
