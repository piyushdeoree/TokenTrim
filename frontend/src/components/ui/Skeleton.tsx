export const Skeleton = ({ className = 'h-20' }: { className?: string }) => <div aria-hidden className={`animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800 ${className}`} />;
