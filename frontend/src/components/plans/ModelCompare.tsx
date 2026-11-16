import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { estimate } from './ModelPricingTable';
import type { ModelPricing } from '@/types/model';
import { useCurrency } from '@/context/CurrencyContext';
import { fmtCurrency } from '@/utils/format';
export function ModelCompare({ models, inTok, outTok }: { models: ModelPricing[]; inTok: number; outTok: number }) {
  const { currency } = useCurrency();
  const costs = models.map((m) => estimate(m, inTok, outTok)); const min = Math.min(...costs);
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Model comparison">
      {models.map((m, i) => (
        <Card key={m.model} title={m.model}>
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between"><dt>Provider</dt><dd>{m.provider}</dd></div>
            <div className="flex justify-between"><dt>Input / 1M</dt><dd>{fmtCurrency(m.input, currency)}</dd></div>
            <div className="flex justify-between"><dt>Output / 1M</dt><dd>{fmtCurrency(m.output, currency)}</dd></div>
            <div className="flex justify-between"><dt>Context</dt><dd>{m.context == null ? 'Not specified' : m.context.toLocaleString()}</dd></div>
            <div className="flex justify-between font-semibold"><dt>Estimated cost</dt><dd>{fmtCurrency(costs[i], currency)}</dd></div>
          </dl>
          {costs[i] === min && <div className="mt-2"><Badge tone="good">Lowest cost</Badge></div>}
        </Card>))}
    </div>
  );
}
