import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Button } from '@/components/ui/Button';
import { Sun, Moon, MenuIcon, PanelLeft } from '@/components/ui/Icons';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
const icon = 'inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-black/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900 dark:hover:bg-white/10 dark:focus-visible:outline-btn';
export function Navbar({ sidebarOpen, mobileOpen, onToggleSidebar, onMenu }: { sidebarOpen: boolean; mobileOpen: boolean; onToggleSidebar: () => void; onMenu: () => void }) {
  const { user, logout } = useAuth(); const { theme, toggleTheme } = useTheme(); const router = useRouter();
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between border-b border-black/10 bg-surface p-3 text-slate-900 dark:border-white/10 dark:text-slate-100">
      <div className="flex items-center gap-2">
        {user && <button type="button" aria-label="Menu" aria-expanded={mobileOpen} onClick={onMenu} className={`${icon} order-first lg:hidden`}><MenuIcon /></button>}
        {user && <button type="button" aria-label="Toggle sidebar" aria-expanded={sidebarOpen} onClick={onToggleSidebar} className={`${icon} order-first hidden transition-transform duration-500 lg:inline-flex ${sidebarOpen ? '' : 'rotate-180'}`}><PanelLeft /></button>}
        {user && <span className={`order-2 hidden overflow-hidden transition-all duration-500 lg:block ${sidebarOpen ? 'pointer-events-none w-0 scale-95 opacity-0' : 'w-[224px] scale-100 opacity-100'}`}>
          <a href="/" aria-label="Go to TokenTrim home"><Image src={theme === 'dark' ? '/Token Trim Heading White.png' : '/Token Trim Heading Black.png'} alt="TokenTrim" width={224} height={31} /></a>
        </span>}
      </div>
      <div className="flex items-center gap-2 text-sm">
        {user && <Link href="/profile" className="hidden sm:inline hover:underline">{user.name}</Link>}
        <button type="button" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'} className={icon}>{theme === 'dark' ? <Sun /> : <Moon />}</button>
        {user && <Button variant="ghost" onClick={() => { logout(); router.push('/'); }}>Sign out</Button>}
      </div>
    </header>
  );
}
