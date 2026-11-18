import { useCallback, useRef, useState } from 'react';
import type { PromptExecutionRequest, PromptExecutionResult } from '@/types/execution';
import { executeOptimizedPrompt } from '@/services/byok/promptExecutionService';
import { toSafeByokMessage } from '@/services/byok/errors';

export function usePromptExecution() {
  const [result, setResult] = useState<PromptExecutionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const run = useCallback(async (request: PromptExecutionRequest) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true); setError(null); setResult(null);
    try { setResult(await executeOptimizedPrompt(request)); }
    catch (e) { setError(toSafeByokMessage(e, 'Prompt execution failed.')); }
    finally { inFlight.current = false; setLoading(false); }
  }, []);
  const clear = useCallback(() => { if (!inFlight.current) { setResult(null); setError(null); } }, []);
  return { result, loading, error, run, clear };
}
