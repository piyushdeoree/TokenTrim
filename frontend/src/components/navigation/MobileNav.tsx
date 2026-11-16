import { NavLinks } from './Sidebar';
import { RecentHistoryToggle } from './RecentHistoryToggle';
export function MobileNav({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return <div className="max-h-[calc(100vh-4rem)] overflow-y-auto border-b border-black/10 bg-surface text-slate-900 dark:border-white/10 dark:text-slate-100 lg:hidden"><NavLinks onNavigate={onClose} /><div className="px-3 pb-3"><RecentHistoryToggle onNavigate={onClose} /></div></div>;
}
