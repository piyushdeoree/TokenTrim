import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { NAV } from '@/utils/constants';
import { RecentHistoryToggle } from './RecentHistoryToggle';
import { useTheme } from '@/context/ThemeContext';
export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useRouter();
  return (
    <nav aria-label="Main" className="flex flex-col gap-1 p-3">
      {NAV.map(([href, label]) => {
        const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
        return <Link key={href} href={href} onClick={onNavigate} aria-current={active ? 'page' : undefined}
          className={`rounded-md px-3 py-2 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900 dark:focus-visible:outline-btn ${active ? 'bg-btn text-slate-900' : 'hover:bg-black/10 dark:hover:bg-white/10'}`}>{label}</Link>;
      })}
    </nav>
  );
}
export function Sidebar({ collapsed }: { collapsed: boolean }) {
  const { theme } = useTheme();
  return (
    <aside aria-label="Sidebar" className={`hidden shrink-0 flex-col overflow-hidden border-r border-black/10 bg-surface text-slate-900 transition-all duration-500 dark:border-white/10 dark:text-slate-100 lg:sticky lg:top-0 lg:flex lg:h-screen ${collapsed ? 'lg:w-0 lg:border-r-0 lg:opacity-0' : 'w-64 lg:w-64 lg:opacity-100'}`}>
      <div className="p-4"><a href="/" aria-label="Go to TokenTrim home"><Image src={theme === 'dark' ? '/Token Trim Heading White.png' : '/Token Trim Heading Black.png'} alt="TokenTrim" width={224} height={31} className="mx-auto block" /></a></div>
      <NavLinks />
      <div className="mt-auto flex min-h-0 flex-1 flex-col justify-end px-3 pb-3"><RecentHistoryToggle /></div>
    </aside>
  );
}
