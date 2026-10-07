import { useState } from 'react';
import { AsyncView } from '@/components/states/AsyncView';
import { Button } from '@/components/ui/Button';
import { ProjectCard } from '@/components/projects/ProjectCard';
import { CreateProjectModal } from '@/components/projects/CreateProjectModal';
import { useProjects } from '@/hooks/useProjects';
export default function Projects() {
  const { state, reload } = useProjects(); const [open, setOpen] = useState(false);
  return (
    <main className="mx-auto max-w-7xl space-y-4 p-4 lg:p-8">
      <div className="flex items-center justify-between"><h1 className="text-xl font-semibold">Projects</h1><Button onClick={() => setOpen(true)}>Create project</Button></div>
      <AsyncView state={state} reload={reload} isEmpty={(d) => d.length === 0} empty={{ title: 'No projects yet', body: 'Create a project to group your saved analyses.' }}>
        {(ps) => <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{ps.map((p) => <ProjectCard key={p.id} p={p} />)}</div>}
      </AsyncView>
      {open && <CreateProjectModal onClose={() => setOpen(false)} onCreated={reload} />}
    </main>
  );
}
