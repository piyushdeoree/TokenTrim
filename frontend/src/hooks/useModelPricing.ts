import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { ModelPricing } from '@/types/model';
export const useModelPricing = () => useAsync(() => load<ModelPricing[]>('/models/pricing'));
