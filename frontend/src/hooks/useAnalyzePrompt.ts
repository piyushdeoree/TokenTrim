import { useState, useCallback } from 'react';
import { analyzePrompt } from '@/services/promptService';
import { toMessage } from '@/services/apiClient';
import type { AnalyzePromptRequest, AnalyzePromptResponse } from '@/types/analysis';
type State =
  | { status: 'idle' } | { status: 'loading' }
  | { status: 'success'; data: AnalyzePromptResponse } | { status: 'error'; message: string };
export function useAnalyzePrompt() {
  const [state, setState] = useState<State>({ status: 'idle' });
  const run = useCallback(async (req: AnalyzePromptRequest) => {
    setState({ status: 'loading' });
    try { setState({ status: 'success', data: await analyzePrompt(req) }); }
    catch (e) { setState({ status: 'error', message: toMessage(e) }); }
  }, []);
  return { state, run, reset: () => setState({ status: 'idle' }) };
}
