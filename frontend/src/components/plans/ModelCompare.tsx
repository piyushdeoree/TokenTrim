import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { estimate } from './ModelPricingTable';
import type { ModelPricing } from '@/types/model';
export function ModelCompare({ models, inTok, outTok }: { models: ModelPricing[]; inTok: number; outTok: number }) {
  const costs = models.map((m) => estimate(m, inTok, outTok)); const min = Math.min(...costs);
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Model comparison">
      {models.map((m, i) => (
        <Card key={m.model} title={m.model}>
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between"><dt>Provider</dt><dd>{m.provider}</dd></div>
            <div className="flex justify-between"><dt>Input / 1M</dt><dd>${m.input}</dd></div>
            <div className="flex justify-between"><dt>Output / 1M</dt><dd>${m.output}</dd></div>
            <div className="flex justify-between"><dt>Context</dt><dd>{m.context.toLocaleString()}</dd></div>
            <div className="flex justify-between font-semibold"><dt>Estimated cost</dt><dd>${costs[i].toFixed(5)}</dd></div>
          </dl>
          {costs[i] === min && <div className="mt-2"><Badge tone="good">Lowest cost</Badge></div>}
        </Card>))}
    </div>
  );
}
