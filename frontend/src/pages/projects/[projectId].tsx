import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import { useAsync } from '@/hooks/useAsync';
import { load } from '@/services/data';
import { send } from '@/services/data';
import { Button } from '@/components/ui/Button';
import { AsyncView } from '@/components/states/AsyncView';
import { TokenCard } from '@/components/metrics/TokenCard';
import { CostCard } from '@/components/metrics/CostCard';
import { ProjectHistoryTable } from '@/components/dashboard/ProjectHistoryTable';
import { Tabs } from '@/components/ui/Tabs';
import type { Project } from '@/types/project';
type History = { id:number; created_at:string; original_prompt:string; optimized_prompt:string; model:string; tokens_saved:number; reduction_percentage:number; original_tokens:number; optimized_tokens:number };
type Usage = { total:number; items:{total_tokens:number; estimated_cost:number}[] };
export default function ProjectDetail() {
  const { query, isReady } = useRouter(); const id = String(query.projectId ?? '');
  const router = useRouter(); const [name, setName] = useState(''); const [description, setDescription] = useState(''); const [message, setMessage] = useState('');
  const { state, reload } = useAsync(async () => {
    const [project, usage, history] = await Promise.all([
      load<Project>(`/projects/${id}`), load<Usage>(`/usage/${id}?limit=200`), load<History[]>(`/history?project_id=${id}&limit=200`)
    ]);
    return { project, usage, history };
  }, [id, isReady]);
  useEffect(() => { if (state.status === 'success') { setName(state.data.project.name); setDescription(state.data.project.description ?? ''); } }, [state]);
  return (
    <main className="mx-auto max-w-5xl space-y-4 p-4 lg:p-8">
      <AsyncView state={state} reload={reload}>
        {(d) => { const p = d.project;
          return (<><div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-xl font-semibold">{p.name}</h1><p className="text-sm opacity-75">{p.description || 'No description'}</p></div>
            <div className="flex flex-wrap gap-2"><input aria-label="Project name" className="rounded border px-2 py-1 dark:bg-slate-950" value={name} onChange={(e) => setName(e.target.value)} />
              <input aria-label="Project description" className="rounded border px-2 py-1 dark:bg-slate-950" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" />
              <Button onClick={async () => { try { await send('put', `/projects/${p.id}`, {name:name.trim(), description:description || null}); setMessage('Project updated.'); reload(); } catch { setMessage('Unable to update project.'); } }}>Save</Button>
              <Button variant="ghost" onClick={async () => { if (!window.confirm('Delete this project?')) return; try { await send('delete', `/projects/${p.id}`); await router.push('/projects'); } catch { setMessage('Unable to delete project.'); } }}>Delete</Button>
            </div></div>{message && <p role="status" className="text-sm">{message}</p>}
            <Tabs tabs={[
              { id: 'usage', label: 'Usage and cost', content: <div className="grid grid-cols-3 gap-3"><TokenCard label="Prompts" value={d.usage.total} /><TokenCard label="Tokens" value={d.usage.items.reduce((n, x) => n + x.total_tokens, 0)} /><CostCard label="Cost" value={d.usage.items.reduce((n, x) => n + x.estimated_cost, 0)} /></div> },
              { id: 'history', label: 'History', content: <ProjectHistoryTable rows={d.history.map((h) => ({ id:h.id, title:h.original_prompt.slice(0, 50), saved:h.tokens_saved, date:new Date(h.created_at).toLocaleString() }))} /> }]} /></>); }}
      </AsyncView>
    </main>
  );
}
