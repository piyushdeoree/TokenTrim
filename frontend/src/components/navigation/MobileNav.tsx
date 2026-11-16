import { NavLinks } from './Sidebar';
export function MobileNav({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return <div className="border-b border-black/10 bg-surface text-slate-900 dark:border-white/10 dark:text-slate-100 lg:hidden"><NavLinks onNavigate={onClose} /></div>;
}
