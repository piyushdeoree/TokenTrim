import { fmtTokens, fmtCurrency, fmtPercent } from '@/utils/format';
it('formats values with INR by default and selected currency symbols without changing amounts', () => {
  expect(fmtTokens(1200)).toBe('1,200');
  expect(fmtCurrency(0.012)).toBe('₹0.0120 INR');
  expect(fmtCurrency(12.5)).toBe('₹12.50 INR');
  expect(fmtCurrency(12.5, 'USD')).toBe('$12.50 USD');
  expect(fmtCurrency(12.5, 'EUR')).toBe('€12.50 EUR');
  expect(fmtCurrency(12.5, 'GBP')).toBe('£12.50 GBP');
  expect(fmtCurrency(12.5, 'JPY')).toBe('¥12.50 JPY');
  expect(fmtCurrency(12.5, 'CAD')).toBe('C$12.50 CAD');
  expect(fmtCurrency(12.5, 'AUD')).toBe('A$12.50 AUD');
  expect(fmtPercent(30.77)).toBe('30.8%');
});
