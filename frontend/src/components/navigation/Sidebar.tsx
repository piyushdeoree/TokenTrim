import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { NAV } from '@/utils/constants';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { ProjectHistoryTable } from '@/components/dashboard/ProjectHistoryTable';
import { useActivity } from '@/hooks/useActivity';
import { useProjects } from '@/hooks/useProjects';
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
function Status({ s, reload }: { s: { status: string }; reload: () => void }) {
  return s.status === 'loading' ? <p className="px-2 text-xs opacity-70">Loading...</p>
    : <p className="px-2 text-xs">Unable to load. <button type="button" className="underline" onClick={reload}>Retry</button></p>;
}
export function Sidebar({ collapsed }: { collapsed: boolean }) {
  const activity = useActivity(); const projects = useProjects();
  return (
    <aside aria-label="Sidebar" className={`hidden w-64 shrink-0 flex-col overflow-y-auto border-r border-black/10 bg-surface text-slate-900 dark:border-white/10 dark:text-slate-100 lg:sticky lg:top-0 lg:h-screen ${collapsed ? 'lg:hidden' : 'lg:flex'}`}>
      <div className="flex items-center gap-2 p-4"><Image src="/logo.svg" alt="" width={28} height={28} /><span className="text-lg font-semibold">TokenTrim</span></div>
      <NavLinks />
      <div className="mt-2 space-y-5 border-t border-black/10 p-3 dark:border-white/10">
        <section aria-labelledby="sb-recent"><h3 id="sb-recent" className="mb-2 px-2 text-sm font-semibold">Recent activity</h3>
          {activity.state.status === 'success' ? <RecentActivity rows={activity.state.data} /> : <Status s={activity.state} reload={activity.reload} />}</section>
        <section aria-labelledby="sb-history"><h3 id="sb-history" className="mb-2 px-2 text-sm font-semibold">Project history</h3>
          {projects.state.status === 'success'
            ? <ProjectHistoryTable compact rows={projects.state.data.flatMap((p) => p.history.map((h, i) => ({ ...h, id: Number(`${p.id}${i}`), project: p.name })))} />
            : <Status s={projects.state} reload={projects.reload} />}</section>
      </div>
    </aside>
  );
}
