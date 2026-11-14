import { useEffect, useState } from 'react';
import type { CollectedRequirements } from './questionnaire';

export function ProjectRequirements({ projectId }: { projectId: string }) {
  const [requirements, setRequirements] = useState<CollectedRequirements | null>(null);
  useEffect(() => {
    setRequirements(null);
    try {
      const saved = localStorage.getItem(`tokentrim:project-requirements:${projectId}`);
      if (saved) setRequirements(JSON.parse(saved) as CollectedRequirements);
    } catch { setRequirements(null); }
  }, [projectId]);
  if (!requirements) return null;
  return <section className="space-y-4 rounded-lg border border-slate-300 bg-card p-4 dark:border-slate-600" aria-labelledby="requirements-heading">
    <div><h2 id="requirements-heading" className="text-lg font-semibold">Project requirements</h2><p className="mt-1 text-sm opacity-70">Your questionnaire responses are saved in this browser.</p></div>
    {requirements.sections.filter(section => section.items.length > 0).map(section => <div key={section.title}><h3 className="mb-2 font-medium">{section.title}</h3><dl className="grid gap-2 sm:grid-cols-2">{section.items.map(item => <div key={item.question} className="rounded-md border border-slate-300 p-3 text-sm dark:border-slate-600"><dt className="text-xs opacity-65">{item.question}</dt><dd className="mt-1 whitespace-pre-wrap">{Array.isArray(item.answer) ? item.answer.join(', ') : item.answer}</dd></div>)}</dl></div>)}
  </section>;
}
