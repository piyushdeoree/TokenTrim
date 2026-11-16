import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';

export const CURRENCIES = [
  { code: 'INR', name: 'Indian Rupee', symbol: '₹' },
  { code: 'USD', name: 'US Dollar', symbol: '$' },
  { code: 'EUR', name: 'Euro', symbol: '€' },
  { code: 'GBP', name: 'British Pound', symbol: '£' },
  { code: 'JPY', name: 'Japanese Yen', symbol: '¥' },
  { code: 'CAD', name: 'Canadian Dollar', symbol: 'C$' },
  { code: 'AUD', name: 'Australian Dollar', symbol: 'A$' },
] as const;

export type CurrencyCode = (typeof CURRENCIES)[number]['code'];
const DEFAULT_CURRENCY: CurrencyCode = 'INR';
const STORAGE_KEY = 'tokentrim:display-currency';
interface CurrencyContextValue { currency: CurrencyCode; setCurrency: (currency: CurrencyCode) => void }
const CurrencyContext = createContext<CurrencyContextValue>({ currency: DEFAULT_CURRENCY, setCurrency: () => {} });

export const useCurrency = () => useContext(CurrencyContext);

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currency, setCurrencyState] = useState<CurrencyCode>(DEFAULT_CURRENCY);
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (CURRENCIES.some((item) => item.code === stored)) setCurrencyState(stored as CurrencyCode);
    } catch {}
  }, []);
  const setCurrency = useCallback((next: CurrencyCode) => {
    setCurrencyState(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch {}
  }, []);
  return <CurrencyContext.Provider value={{ currency, setCurrency }}>{children}</CurrencyContext.Provider>;
}
