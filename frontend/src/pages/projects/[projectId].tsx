import { useRouter } from 'next/router';
import { AsyncView } from '@/components/states/AsyncView';
import { TokenCard } from '@/components/metrics/TokenCard';
import { CostCard } from '@/components/metrics/CostCard';
import { ProjectHistoryTable } from '@/components/dashboard/ProjectHistoryTable';
import { Tabs } from '@/components/ui/Tabs';
import { useProjects } from '@/hooks/useProjects';
export default function ProjectDetail() {
  const { query } = useRouter();
  const { state, reload } = useProjects(); // TODO: swap to GET /api/projects/:id when available
  return (
    <main className="mx-auto max-w-5xl space-y-4 p-4 lg:p-8">
      <AsyncView state={state} reload={reload}>
        {(ps) => { const p = ps.find((x) => x.id === query.projectId);
          if (!p) return <p>Project not found.</p>;
          return (<><h1 className="text-xl font-semibold">{p.name}</h1>
            <Tabs tabs={[
              { id: 'usage', label: 'Usage and cost', content: <div className="grid grid-cols-3 gap-3"><TokenCard label="Prompts" value={p.prompts} /><TokenCard label="Tokens" value={p.tokens} /><CostCard label="Cost" value={p.cost} /></div> },
              { id: 'history', label: 'History', content: <ProjectHistoryTable rows={p.history.map((h, i) => ({ ...h, id: i }))} /> }]} /></>); }}
      </AsyncView>
    </main>
  );
}
