import type { Config } from 'tailwindcss';
const config: Config = {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx}'],
  theme: { extend: { colors: {
    page: 'var(--color-page)', surface: 'var(--color-surface)', chart: 'var(--color-chart)', btn: 'var(--color-btn)', card: 'var(--color-card)',
  } } },
  plugins: [],
};
export default config;
