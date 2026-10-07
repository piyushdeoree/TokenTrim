import { SelectHTMLAttributes } from 'react';
export function Select({ label, error, children, ...r }: SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string }) {
  const id = r.id ?? label.replace(/\s/g, '-').toLowerCase();
  return (
    <div><label htmlFor={id} className="mb-1 block text-sm font-medium">{label}</label>
      <select id={id} aria-invalid={!!error} {...r} className="w-full rounded-md border border-slate-300 bg-white p-2 text-sm dark:border-slate-600 dark:bg-slate-950">{children}</select>
      {error && <p className="mt-1 text-xs text-red-700 dark:text-red-400">{error}</p>}</div>
  );
}
