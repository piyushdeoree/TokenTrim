import { MAX_PROMPT_CHARS } from '@/utils/validation';
export function PromptEditor({ value, onChange, error }: { value: string; onChange: (v: string) => void; error?: string }) {
  return (
    <div>
      <label htmlFor="prompt" className="mb-1 block text-sm font-medium text-slate-900 dark:text-slate-100">Original prompt</label>
      <textarea id="prompt" value={value} onChange={(e) => onChange(e.target.value)} rows={16}
        placeholder="Enter or paste your prompt"
        aria-invalid={!!error} aria-describedby={error ? 'prompt-err' : 'prompt-count'}
        className="w-full resize-y rounded-md border border-slate-300 bg-white p-3 font-mono text-sm text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-600 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100" />
      <div className="mt-1 flex justify-between text-xs">
        {error ? <p id="prompt-err" className="text-red-700 dark:text-red-400">{error}</p> : <span />}
        <span id="prompt-count" className="text-slate-500">{value.length.toLocaleString()} / {MAX_PROMPT_CHARS.toLocaleString()}</span>
      </div>
    </div>
  );
}
