import { useAsync } from './useAsync';
import { load } from '@/services/data';
import { pricingMock } from '@/services/mocks/modelPricing.mock';
import type { ModelPricing } from '@/types/model';
export const useModelPricing = () => useAsync(() => load<ModelPricing[]>('/models/pricing', pricingMock));
