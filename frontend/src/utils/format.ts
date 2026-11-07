export const fmtTokens = (n: number) => n.toLocaleString();
export const fmtCurrency = (n: number) => `$${n.toFixed(n < 1 ? 4 : 2)}`;
export const fmtPercent = (n: number) => `${n.toFixed(1)}%`;
