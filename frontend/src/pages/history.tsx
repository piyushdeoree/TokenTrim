import { useAsync } from '@/hooks/useAsync';
import { load } from '@/services/data';
import { AsyncView } from '@/components/states/AsyncView';
import { Card } from '@/components/ui/Card';
import { useState } from 'react';
import { Button } from '@/components/ui/Button';

type Item = { id: number; created_at: string; original_prompt: string; optimized_prompt: string; model: string;
  project: string | null; original_tokens: number; optimized_tokens: number; tokens_saved: number; reduction_percentage: number };
export default function History() {
  const [offset, setOffset] = useState(0);
  const { state, reload } = useAsync(() => load<Item[]>(`/history?limit=50&offset=${offset}`), [offset]);
  return <main className="mx-auto max-w-5xl space-y-4 p-4 lg:p-8"><h1 className="text-xl font-semibold">Prompt history</h1>
    <AsyncView state={state} reload={reload} isEmpty={(items) => !items.length}
      empty={{ title: 'No analyses yet', body: 'Successful prompt optimizations are saved here automatically.' }}>
      {(items) => <div className="space-y-3">{items.map((item) => <Card key={item.id} title={`${item.model} · ${new Date(item.created_at).toLocaleString()}`}>
        <p className="mb-2 text-sm">{item.project ?? 'Unassigned'} · {item.tokens_saved} tokens saved ({item.reduction_percentage}% reduction)</p>
        <details className="text-sm"><summary className="cursor-pointer font-medium">Inspect prompt and result</summary>
          <div className="mt-3 grid gap-3 md:grid-cols-2"><section><h2 className="font-semibold">Original ({item.original_tokens} tokens)</h2><pre className="mt-1 whitespace-pre-wrap break-words rounded bg-black/5 p-3 dark:bg-white/5">{item.original_prompt}</pre></section>
          <section><h2 className="font-semibold">Optimized ({item.optimized_tokens} tokens)</h2><pre className="mt-1 whitespace-pre-wrap break-words rounded bg-black/5 p-3 dark:bg-white/5">{item.optimized_prompt}</pre></section></div>
      </details></Card>)}<div className="flex justify-between"><Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous</Button><Button variant="ghost" disabled={items.length < 50} onClick={() => setOffset(offset + 50)}>Next</Button></div></div>}
    </AsyncView>
  </main>;
}
