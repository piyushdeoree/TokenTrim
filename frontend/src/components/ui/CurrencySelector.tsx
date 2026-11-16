import { Select } from '@/components/ui/Select';
import { CURRENCIES, useCurrency } from '@/context/CurrencyContext';

export function CurrencySelector() {
  const { currency, setCurrency } = useCurrency();
  return (
    <div className="min-w-[10rem] flex-1 sm:flex-none sm:min-w-48">
      <Select label="Display currency" value={currency} onChange={(event) => setCurrency(event.target.value as typeof currency)}>
        {CURRENCIES.map(({ code, name, symbol }) => <option key={code} value={code}>{code} — {name} ({symbol})</option>)}
      </Select>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">Symbol only; amounts are not converted.</p>
    </div>
  );
}
