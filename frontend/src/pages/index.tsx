import Image from 'next/image';
import Link from 'next/link';
import { useState } from 'react';
import { AnalyzeButton } from '@/components/token-trim/AnalyzeButton';
import { Button } from '@/components/ui/Button';
import { PromptEditor } from '@/components/token-trim/PromptEditor';
import { ModelSelector } from '@/components/token-trim/ModelSelector';
import { AnalysisResult } from '@/components/token-trim/AnalysisResult';
import { SaveAnalysisModal } from '@/components/token-trim/SaveAnalysisModal';
import { LoadingState, EmptyState, ErrorState } from '@/components/states/States';
import { useAnalyzePrompt } from '@/hooks/useAnalyzePrompt';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { validateAnalyzeForm } from '@/utils/validation';

export default function TokenTrimPage() {
  const { user } = useAuth(); const { theme } = useTheme();
  const [prompt, setPrompt] = useState(''); const [model, setModel] = useState('');
  const [errors, setErrors] = useState<{ prompt?: string; model?: string }>({});
  const [saving, setSaving] = useState(false);
  const { state, run } = useAnalyzePrompt();

  const submit = () => {
    const e = validateAnalyzeForm(prompt, model); setErrors(e);
    if (!Object.keys(e).length) run({ prompt, model });
  };

  return (
    <>
    <main className={`mx-auto grid max-w-7xl gap-6 p-4 lg:grid-cols-2 lg:p-8 ${!user ? 'pointer-events-none blur-sm' : ''}`}>
      {!user && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-surface p-4 lg:col-span-2">
          <p className="text-sm font-medium">Sign in to save analyses and track usage on your dashboard.</p>
          <div className="flex gap-2"><Button>Sign in</Button><Button variant="ghost">Create account</Button></div>
        </div>
      )}
      <div className="space-y-4">
        <PromptEditor value={prompt} onChange={setPrompt} error={errors.prompt} />
        <ModelSelector value={model} onChange={setModel} error={errors.model} />
        <AnalyzeButton onClick={submit} loading={state.status === 'loading'} />
      </div>
      <div aria-live="polite">
        <h2 className="mb-4 text-xl font-semibold">Prompt analysis</h2>
        {state.status === 'idle' && <EmptyState title="No analysis yet" body="Paste a prompt, pick a model, and select Analyze prompt." />}
        {state.status === 'loading' && <LoadingState />}
        {state.status === 'error' && <ErrorState message={state.message} onRetry={submit} />}
        {state.status === 'success' && <AnalysisResult data={state.data} original={prompt} onSave={() => setSaving(true)} />}
        {saving && state.status === 'success' && <SaveAnalysisModal prompt={prompt} model={model} result={state.data} onClose={() => setSaving(false)} />}
      </div>
    </main>
    {!user && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-md">
      <div role="dialog" aria-modal="true" aria-label="Sign in to TokenTrim" className="w-full max-w-md rounded-2xl border border-black/10 bg-card p-8 text-center shadow-2xl dark:border-white/10">
        <Image src={theme === 'dark' ? '/TokenTrim Logo.png' : '/TokenTrim Logo2.png'} alt="TokenTrim logo" width={56} height={56} className="mx-auto mb-4" priority />
        <h2 className="text-2xl font-semibold">Welcome to TokenTrim</h2>
        <p className="mt-2 text-sm opacity-75">Sign in or create an account to use the TokenTrim platform.</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link href="/login" className="inline-flex flex-1 items-center justify-center rounded-md bg-btn px-4 py-2 text-sm font-semibold text-slate-900">Login</Link>
          <Link href="/register" className="inline-flex flex-1 items-center justify-center rounded-md border border-slate-500/50 px-4 py-2 text-sm font-semibold hover:bg-black/10 dark:hover:bg-white/10">Sign Up</Link>
        </div>
      </div>
    </div>}
    </>
  );
}
