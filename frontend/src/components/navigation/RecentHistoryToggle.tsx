import { useEffect, useId, useState } from 'react';
import Link from 'next/link';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { useActivity } from '@/hooks/useActivity';

function ActivityState({ state, reload }: { state: ReturnType<typeof useActivity>['state']; reload: () => void }) {
  if (state.status === 'loading') return <p className="px-2 py-2 text-xs opacity-70">Loading history...</p>;
  if (state.status === 'error') return <p className="px-2 py-2 text-xs">Unable to load history. <button type="button" className="underline" onClick={reload}>Retry</button></p>;
  return <RecentActivity rows={state.data} />;
}

export function RecentHistoryToggle({ onNavigate }: { onNavigate?: () => void }) {
  const [expanded, setExpanded] = useState(true);
  const listId = `recent-history-list-${useId().replace(/:/g, '')}`;
  const activity = useActivity();
  useEffect(() => {
    try { setExpanded(localStorage.getItem('recentHistoryExpanded') !== '0'); } catch {}
  }, []);
  const toggleExpanded = () => setExpanded((value) => {
    const next = !value;
    try { localStorage.setItem('recentHistoryExpanded', next ? '1' : '0'); } catch {}
    return next;
  });
  return (
    <section aria-label="Recent history" className="flex min-h-0 flex-col border-t border-black/10 dark:border-white/10">
      <button type="button" aria-expanded={expanded} aria-controls={listId} onClick={toggleExpanded}
        className="flex w-full shrink-0 items-center justify-between rounded-md px-2 py-3 text-left text-sm font-semibold hover:bg-black/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900 dark:hover:bg-white/10 dark:focus-visible:outline-btn">
        <span>View Recent History</span>
        <span aria-hidden="true" className={`inline-block transition-transform ${expanded ? 'rotate-180' : ''}`}>⌄</span>
      </button>
      {expanded && <>
        <div id={listId} className="max-h-[30vh] min-h-0 overflow-y-auto overscroll-contain px-1 pb-2 lg:max-h-[38vh]">
          <ActivityState state={activity.state} reload={activity.reload} />
        </div>
        <Link href="/history" onClick={onNavigate} className="shrink-0 px-2 py-2 text-sm font-medium underline">View full prompt history</Link>
      </>}
    </section>
  );
}
