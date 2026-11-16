import { DataTable } from '@/components/ui/DataTable';
import type { ModelPricing } from '@/types/model';
import { useCurrency } from '@/context/CurrencyContext';
import { fmtCurrency } from '@/utils/format';
export const estimate = (m: ModelPricing, i: number, o: number) => (i * m.input + o * m.output) / 1e6;
export function ModelPricingTable({ rows, selected, onToggle, inTok, outTok }: { rows: ModelPricing[]; selected: string[]; onToggle: (m: string) => void; inTok: number; outTok: number }) {
  const { currency } = useCurrency();
  return <DataTable caption="Model pricing per 1M tokens" rows={rows.map((r) => ({ ...r, id: r.model }))} cols={[
    { header: 'Compare', cell: (r) => <input type="checkbox" aria-label={`Compare ${r.model}`} checked={selected.includes(r.model)} onChange={() => onToggle(r.model)} /> },
    { header: 'Model', cell: (r) => r.model }, { header: 'Provider', cell: (r) => r.provider },
    { header: 'Input / 1M', cell: (r) => fmtCurrency(r.input, currency) }, { header: 'Output / 1M', cell: (r) => fmtCurrency(r.output, currency) },
    { header: 'Context', cell: (r) => r.context == null ? 'Not specified' : r.context.toLocaleString() },
    { header: 'Estimated cost', cell: (r) => fmtCurrency(estimate(r, inTok, outTok), currency) }]} />;
}
