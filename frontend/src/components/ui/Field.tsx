import { InputHTMLAttributes } from 'react';
export function Field({ label, error, ...r }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string }) {
  const id = r.id ?? label.replace(/\s/g, '-').toLowerCase();
  return (
    <div><label htmlFor={id} className="mb-1 block text-sm font-medium">{label}</label>
      <input id={id} aria-invalid={!!error} {...r} className="w-full rounded-md border border-slate-300 bg-white p-2 text-sm dark:border-slate-600 dark:bg-slate-950" />
      {error && <p className="mt-1 text-xs text-red-700 dark:text-red-400">{error}</p>}</div>
  );
}
