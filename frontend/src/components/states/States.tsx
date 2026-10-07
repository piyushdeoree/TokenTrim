import { Button } from '@/components/ui/Button';
export const LoadingState = ({ text = 'Analyzing prompt...' }) => (
  <div role="status" aria-live="polite" className="animate-pulse space-y-3 p-2">
    <p className="text-sm text-slate-600 dark:text-slate-400">{text}</p>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-20 rounded-lg bg-slate-200 dark:bg-slate-800" />)}
    </div>
  </div>
);
export const EmptyState = ({ title, body }: { title: string; body: string }) => (
  <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center dark:border-slate-600">
    <p className="font-semibold text-slate-900 dark:text-slate-100">{title}</p>
    <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{body}</p>
  </div>
);
export const ErrorState = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
    <p className="text-sm font-medium">{message}</p>
    {onRetry && <Button variant="ghost" className="mt-3" onClick={onRetry}>Try again</Button>}
  </div>
);
