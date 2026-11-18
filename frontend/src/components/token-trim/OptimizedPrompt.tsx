import { Button } from '@/components/ui/Button';
import { PromptComparison } from './PromptComparison';
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard';
export function OptimizedPrompt({ original, optimized, onSave }: { original: string; optimized: string; onSave?: () => void }) {
  const { copied, error, copy } = useCopyToClipboard();
  return (<>
    <PromptComparison original={original} optimized={optimized} />
    <div className="mt-3 flex flex-wrap gap-2">
      <Button onClick={() => copy(optimized)}>{copied ? 'Copied' : 'Copy optimized prompt'}</Button>
      {onSave && <Button variant="ghost" onClick={onSave}>Save analysis</Button>}
    </div>
    {error && <p role="alert" className="mt-2 text-sm text-red-700 dark:text-red-400">{error}</p>}
    {copied && <p role="status" className="sr-only">Prompt copied to clipboard.</p>}
  </>);
}
