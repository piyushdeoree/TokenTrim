import Image from 'next/image';
import { Button } from '@/components/ui/Button';
import { useTheme } from '@/context/ThemeContext';
export const LoadingState = ({ text = 'Analyzing prompt...' }) => (
  <LoadingContent text={text} />
);
function LoadingContent({ text }: { text: string }) {
  const { theme } = useTheme();
  return <div role="status" aria-live="polite" className="flex min-h-32 flex-col items-center justify-center gap-3 p-6">
    <div className="relative flex h-14 w-14 items-center justify-center">
      <span className="absolute inset-0 animate-spin rounded-full border-2 border-btn/30 border-t-btn" />
      <Image src={theme === 'dark' ? '/TokenTrim Logo.png' : '/TokenTrim Logo2.png'} alt="" width={30} height={30} />
    </div>
    <p className="animate-pulse text-sm text-slate-600 dark:text-slate-400">{text}</p>
  </div>;
}
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
