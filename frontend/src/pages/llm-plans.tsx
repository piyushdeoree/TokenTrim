import { useState } from 'react';
import { AsyncView } from '@/components/states/AsyncView';
import { ModelPricingTable } from '@/components/plans/ModelPricingTable';
import { ModelCompare } from '@/components/plans/ModelCompare';
import { useModelPricing } from '@/hooks/useModelPricing';
export default function LlmPlans() {
  const { state, reload } = useModelPricing();
  const [sel, setSel] = useState<string[]>([]); const [inTok, setIn] = useState(1000); const [outTok, setOut] = useState(500);
  const toggle = (m: string) => setSel((s) => (s.includes(m) ? s.filter((x) => x !== m) : [...s, m]));
  return (
    <main className="mx-auto max-w-5xl space-y-4 p-4 lg:p-8">
      <h1 className="text-xl font-semibold">LLM plans</h1>
      <div className="flex flex-wrap gap-4 text-sm">
        <label>Input tokens <input type="number" min={0} value={inTok} onChange={(e) => setIn(Math.max(0, +e.target.value))} className="ml-1 w-24 rounded border p-1 dark:bg-slate-950" /></label>
        <label>Output tokens <input type="number" min={0} value={outTok} onChange={(e) => setOut(Math.max(0, +e.target.value))} className="ml-1 w-24 rounded border p-1 dark:bg-slate-950" /></label>
      </div>
      <AsyncView state={state} reload={reload} isEmpty={(d) => !d.length} empty={{ title: 'No pricing data', body: 'Model prices are not available yet.' }}>
        {(rows) => (<>
          <ModelPricingTable rows={rows} selected={sel} onToggle={toggle} inTok={inTok} outTok={outTok} />
          {sel.length >= 2 ? <ModelCompare models={rows.filter((r) => sel.includes(r.model))} inTok={inTok} outTok={outTok} />
            : <p className="text-sm text-slate-600 dark:text-slate-400">Select two or more models to compare them side by side.</p>}
        </>)}
      </AsyncView>
    </main>
  );
}
