import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { useProviders } from '@/context/ProviderContext';
import { useProviderModels } from '@/hooks/useProviderModels';
import { usePromptExecution } from '@/hooks/usePromptExecution';
import { ExecutionResult } from './ExecutionResult';
import type { ProviderId } from '@/types/provider';

export function PromptExecutionPanel({ optimizedPrompt, estimatedCost, estimatedSaving }: {
  optimizedPrompt: string; estimatedCost?: number | null; estimatedSaving?: number | null;
}) {
  const { connections } = useProviders();
  const connected = useMemo(() => connections.filter((item) => item.status === 'connected'), [connections]);
  const [providerId, setProviderId] = useState<ProviderId | ''>('');
  const [modelId, setModelId] = useState('');
  const activeConnection = connected.find((item) => item.provider === providerId);
  const { models, loading: modelsLoading, error: modelsError, retry: retryModels } = useProviderModels(providerId || null, !!activeConnection);
  const execution = usePromptExecution();
  useEffect(() => {
    if (!connected.some((item) => item.provider === providerId)) setProviderId(connected[0]?.provider ?? '');
  }, [connected, providerId]);
  useEffect(() => { setModelId(models[0]?.id ?? ''); }, [models]);
  const run = () => {
    if (!providerId || !modelId) return;
    void execution.run({ prompt: optimizedPrompt, provider: providerId, model: modelId });
  };
  return <section className="space-y-4" aria-label="Run optimized prompt">
    <Card title="Run optimized prompt">
      <p className="mb-4 text-sm opacity-75">Choose a connected provider and model to run the optimized prompt.</p>
      {connected.length === 0 ? <div className="rounded-md border border-dashed border-black/20 p-4 text-sm dark:border-white/20"><p>No providers connected yet.</p><Link className="mt-2 inline-block font-medium underline" href="/providers">Manage provider connections</Link></div> : <div className="grid gap-4 sm:grid-cols-2">
        <Select label="Provider" value={providerId} disabled={execution.loading} onChange={(e) => { setProviderId(e.target.value as ProviderId); setModelId(''); execution.clear(); }}>
          {connected.map((item) => <option key={item.provider} value={item.provider}>{item.provider === 'gemini' ? 'Google Gemini' : item.provider === 'anthropic' ? 'Anthropic Claude' : 'OpenAI'} · Connected</option>)}
        </Select>
        <Select label="Execution model" value={modelId} onChange={(e) => { setModelId(e.target.value); execution.clear(); }} disabled={execution.loading || modelsLoading || !models.length}>
          {!models.length && <option value="">{modelsLoading ? 'Loading models…' : modelsError ? 'Unable to load models' : 'No models available'}</option>}
          {models.map((model) => <option key={model.id} value={model.id}>{model.name} · {model.availability === 'demo' ? 'Demo' : 'Live'}</option>)}
        </Select>
      </div>}
      {modelsError && <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-400">{modelsError} <button type="button" className="underline" onClick={retryModels}>Retry</button></p>}
      {connected.length > 0 && <div className="mt-4 flex flex-wrap items-center gap-3"><Button onClick={run} loading={execution.loading} disabled={!providerId || !modelId || execution.loading}>Run Optimized Prompt</Button><span className="text-xs opacity-65">{models.some((model) => model.availability === 'demo') ? 'Demo model catalog · not live availability' : 'Model availability supplied by the backend'}</span></div>}
      {execution.error && <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-400">{execution.error}</p>}
      {execution.loading && <p role="status" className="mt-4 animate-pulse text-sm">Preparing demo response…</p>}
    </Card>
    {execution.result && <ExecutionResult result={execution.result} estimatedCost={estimatedCost} estimatedSaving={estimatedSaving} />}
  </section>;
}
