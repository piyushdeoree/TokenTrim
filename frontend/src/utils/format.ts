export const fmtTokens = (n: number) => n.toLocaleString();
import { CURRENCIES, type CurrencyCode } from '@/context/CurrencyContext';
export const fmtCurrency = (n: number, currency: CurrencyCode = 'INR') => {
  const symbol = CURRENCIES.find((item) => item.code === currency)?.symbol ?? '₹';
  return `${symbol}${n.toFixed(n < 1 ? 4 : 2)} ${currency}`;
};
export const fmtPercent = (n: number) => `${n.toFixed(1)}%`;
