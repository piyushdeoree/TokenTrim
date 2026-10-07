import { ButtonHTMLAttributes } from 'react';
type P = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost'; loading?: boolean };
export function Button({ variant = 'primary', loading, children, disabled, className = '', ...r }: P) {
  const v = variant === 'primary'
    ? 'bg-btn text-slate-900 hover:brightness-95 disabled:opacity-60'
    : 'border border-slate-500/50 hover:bg-black/10 dark:hover:bg-white/10 disabled:opacity-60';
  return (
    <button type="button" {...r} disabled={disabled || loading} aria-busy={loading}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 dark:focus-visible:outline-btn disabled:cursor-not-allowed ${v} ${className}`}>
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-900/30 border-t-slate-900" aria-hidden />}
      {children}
    </button>
  );
}
