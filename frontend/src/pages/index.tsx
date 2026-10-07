import Image from 'next/image';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import { AnalyzeButton } from '@/components/token-trim/AnalyzeButton';
import { Button } from '@/components/ui/Button';
import { PromptEditor } from '@/components/token-trim/PromptEditor';
import { ModelSelector } from '@/components/token-trim/ModelSelector';
import { AnalysisResult } from '@/components/token-trim/AnalysisResult';
import { SaveAnalysisModal } from '@/components/token-trim/SaveAnalysisModal';
import { AuthModal, AuthMode } from '@/components/auth/AuthModal';
import { LoadingState, EmptyState, ErrorState } from '@/components/states/States';
import { useAnalyzePrompt } from '@/hooks/useAnalyzePrompt';
import { useAuth } from '@/context/AuthContext';
import { validateAnalyzeForm } from '@/utils/validation';

export default function TokenTrimPage() {
  const router = useRouter(); const { user } = useAuth();
  const [prompt, setPrompt] = useState(''); const [model, setModel] = useState('');
  const [errors, setErrors] = useState<{ prompt?: string; model?: string }>({});
  const [saving, setSaving] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode | null>(null);
  const { state, run } = useAnalyzePrompt();

  // /?auth=login or /?auth=register opens the modal (used by route guard and old /login URLs)
  const q = router.query?.auth;
  useEffect(() => { if (q === 'login' || q === 'register') setAuthMode(q); }, [q]);
  const closeAuth = () => { setAuthMode(null); if (q) router.replace('/', undefined, { shallow: true }); };

  const submit = () => {
    const e = validateAnalyzeForm(prompt, model); setErrors(e);
    if (!Object.keys(e).length) run({ prompt, model });
  };

  return (
    <main className="mx-auto grid max-w-7xl gap-6 p-4 lg:grid-cols-2 lg:p-8">
      {!user && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-surface p-4 lg:col-span-2">
          <p className="text-sm font-medium">Sign in to save analyses and track usage on your dashboard.</p>
          <div className="flex gap-2"><Button onClick={() => setAuthMode('login')}>Sign in</Button><Button variant="ghost" onClick={() => setAuthMode('register')}>Create account</Button></div>
        </div>
      )}
      <div className="space-y-4">
        <h1 className="flex items-center gap-3 text-xl font-semibold">
          <Image src="/logo.svg" alt="TokenTrim logo" width={36} height={36} priority />Token Trim
        </h1>
        <PromptEditor value={prompt} onChange={setPrompt} error={errors.prompt} />
        <ModelSelector value={model} onChange={setModel} error={errors.model} />
        <AnalyzeButton onClick={submit} loading={state.status === 'loading'} />
      </div>
      <div aria-live="polite">
        <h2 className="mb-4 text-xl font-semibold">Prompt analysis</h2>
        {state.status === 'idle' && <EmptyState title="No analysis yet" body="Paste a prompt, pick a model, and select Analyze prompt." />}
        {state.status === 'loading' && <LoadingState />}
        {state.status === 'error' && <ErrorState message={state.message} onRetry={submit} />}
        {state.status === 'success' && <AnalysisResult data={state.data} original={prompt} onSave={() => (user ? setSaving(true) : setAuthMode('login'))} />}
        {saving && state.status === 'success' && <SaveAnalysisModal prompt={prompt} model={model} result={state.data} onClose={() => setSaving(false)} />}
      </div>
      {authMode && <AuthModal mode={authMode} onModeChange={setAuthMode} onClose={closeAuth} onSuccess={() => { setAuthMode(null); router.push('/dashboard'); }} />}
    </main>
  );
}
