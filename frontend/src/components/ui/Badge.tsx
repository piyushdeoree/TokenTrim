const T = { neutral: 'bg-slate-200 text-slate-900', good: 'bg-teal-100 text-teal-900', warn: 'bg-amber-200 text-amber-950', bad: 'bg-red-200 text-red-950' };
export function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: keyof typeof T }) {
  return <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${T[tone]}`}>{children}</span>;
}
