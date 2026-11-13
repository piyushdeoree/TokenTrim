import { Select } from '@/components/ui/Select';
import { useModelPricing } from '@/hooks/useModelPricing';
import { useAuth } from '@/context/AuthContext';
export function ModelSelector({ value, onChange, error }: { value: string; onChange: (v: string) => void; error?: string }) {
  const { user } = useAuth();
  const { state } = useModelPricing(!!user); // model list comes from GET /models/pricing
  const models = state.status === 'success' ? state.data : [];
  return (
    <Select label="Model" value={value} onChange={(e) => onChange(e.target.value)} error={error} disabled={state.status === 'loading'}>
      <option value="">{state.status === 'loading' ? 'Loading models...' : state.status === 'error' ? 'Unable to load models' : 'Select a model'}</option>
      {models.map((m) => <option key={m.model} value={m.model}>{m.model}</option>)}
    </Select>
  );
}
