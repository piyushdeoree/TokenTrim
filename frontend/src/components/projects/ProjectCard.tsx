import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { fmtCurrency, fmtTokens } from '@/utils/format';
import type { Project } from '@/types/project';
export const ProjectCard = ({ p }: { p: Project }) => (
  <Card><Link href={`/projects/${p.id}`} className="font-semibold text-teal-700 underline dark:text-teal-400">{p.name}</Link>
    <p className="mt-2 text-sm">{p.prompts} prompts · {fmtTokens(p.tokens)} tokens · {fmtCurrency(p.cost)}</p></Card>
);
