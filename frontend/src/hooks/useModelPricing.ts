import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { ModelPricing } from '@/types/model';
export const useModelPricing = (enabled = true) =>
  useAsync(async () => {
    if (!enabled) return [];
    type Pricing = { model:string; provider:string; input_price_per_1k:number; output_price_per_1k:number };
    type Model = { name:string; context_window:number|null };
    const [pricing, models] = await Promise.all([load<Pricing[]>('/models/pricing'), load<Model[]>('/models')]);
    const context = new Map(models.map((m) => [m.name, m.context_window]));
    return pricing.map((p) => ({ model:p.model, provider:p.provider, input:p.input_price_per_1k * 1000,
      output:p.output_price_per_1k * 1000, context:context.get(p.model) ?? null }));
  }, [enabled]);
