import Image from 'next/image';
import { useRouter } from 'next/router';
import { Button } from '@/components/ui/Button';
import { Sun, Moon, MenuIcon, PanelLeft } from '@/components/ui/Icons';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
const icon = 'inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-black/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-slate-900 dark:hover:bg-white/10 dark:focus-visible:outline-btn';
export function Navbar({ sidebarOpen, mobileOpen, onToggleSidebar, onMenu }: { sidebarOpen: boolean; mobileOpen: boolean; onToggleSidebar: () => void; onMenu: () => void }) {
  const { user, logout } = useAuth(); const { theme, toggleTheme } = useTheme(); const router = useRouter();
  return (
    <header className="flex items-center justify-between border-b border-black/10 bg-surface p-3 text-slate-900 dark:border-white/10 dark:text-slate-100">
      <div className="flex items-center gap-2">
        {user ? (<>
          <button type="button" aria-label="Menu" aria-expanded={mobileOpen} onClick={onMenu} className={`${icon} lg:hidden`}><MenuIcon /></button>
          <button type="button" aria-label="Toggle sidebar" aria-expanded={sidebarOpen} onClick={onToggleSidebar} className={`${icon} hidden lg:inline-flex`}><PanelLeft /></button>
          <span className="font-semibold lg:hidden">TokenTrim</span>
        </>) : (<span className="flex items-center gap-2 font-semibold"><Image src="/logo.svg" alt="" width={24} height={24} />TokenTrim</span>)}
      </div>
      <div className="flex items-center gap-2 text-sm">
        {user && <span className="hidden sm:inline">{user.name}</span>}
        <button type="button" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'} className={icon}>{theme === 'dark' ? <Sun /> : <Moon />}</button>
        {user && <Button variant="ghost" onClick={() => { logout(); router.push('/'); }}>Sign out</Button>}
      </div>
    </header>
  );
}
