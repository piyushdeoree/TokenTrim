import { ReactNode, useEffect, useState } from 'react';
import { Navbar } from '@/components/navigation/Navbar';
import { Sidebar } from '@/components/navigation/Sidebar';
import { MobileNav } from '@/components/navigation/MobileNav';
import { useAuth } from '@/context/AuthContext';
export function AppLayout({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [mobile, setMobile] = useState(false); const [collapsed, setCollapsed] = useState(false);
  useEffect(() => { try { setCollapsed(localStorage.getItem('sidebarCollapsed') === '1'); } catch {} }, []);
  const toggleSidebar = () => { const next = !collapsed; setCollapsed(next); try { localStorage.setItem('sidebarCollapsed', next ? '1' : '0'); } catch {} };
  return (
    <div className="min-h-screen lg:flex">
      {user && <Sidebar collapsed={collapsed} />}
      <div className="min-w-0 flex-1">
        <Navbar sidebarOpen={!collapsed} mobileOpen={mobile} onToggleSidebar={toggleSidebar} onMenu={() => setMobile(!mobile)} />
        {user && <MobileNav open={mobile} onClose={() => setMobile(false)} />}
        {children}
      </div>
    </div>
  );
}
