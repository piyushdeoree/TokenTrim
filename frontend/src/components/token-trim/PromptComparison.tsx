export function PromptComparison({ original, optimized }: { original: string; optimized: string }) {
  const box = 'max-h-64 overflow-auto whitespace-pre-wrap rounded-md border p-3 font-mono text-xs';
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div><h3 className="mb-1 text-sm font-medium text-slate-900 dark:text-slate-100">Original</h3>
        <pre className={`${box} border-slate-300 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200`}>{original}</pre></div>
      <div><h3 className="mb-1 text-sm font-medium text-slate-900 dark:text-slate-100">Optimized</h3>
        <pre className={`${box} border-teal-600 bg-teal-50 text-teal-950 dark:bg-teal-950 dark:text-teal-50`}>{optimized}</pre></div>
    </div>
  );
}
