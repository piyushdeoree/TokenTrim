import { fmtTokens, fmtCurrency, fmtPercent } from '@/utils/format';
it('formats values', () => { expect(fmtTokens(1200)).toBe('1,200'); expect(fmtCurrency(0.012)).toBe('$0.0120'); expect(fmtCurrency(12.5)).toBe('$12.50'); expect(fmtPercent(30.77)).toBe('30.8%'); });
