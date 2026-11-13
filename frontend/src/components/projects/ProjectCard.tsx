import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import type { Project } from '@/types/project';
export const ProjectCard = ({ p }: { p: Project }) => (
  <Card><Link href={`/projects/${p.id}`} className="font-semibold text-teal-700 underline dark:text-teal-400">{p.name}</Link>
    <p className="mt-2 text-sm">{p.description || 'No description'} · Created {new Date(p.created_at).toLocaleDateString()}</p></Card>
);
