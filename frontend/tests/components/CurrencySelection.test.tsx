import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CurrencyProvider } from '@/context/CurrencyContext';
import { CurrencySelector } from '@/components/ui/CurrencySelector';
import { CostCard } from '@/components/metrics/CostCard';
import { SavingsCard } from '@/components/metrics/SavingsCard';
import { ModelCostComparison } from '@/components/token-trim/ModelCostComparison';

const setup = () => render(<CurrencyProvider><div><CurrencySelector /><CostCard label="Dashboard cost" value={1.25} /><SavingsCard label="Savings amount" value={1.25} /><ModelCostComparison /></div></CurrencyProvider>);

beforeEach(() => localStorage.clear());
afterEach(() => localStorage.clear());

it('defaults to INR and updates currency labels without changing displayed amounts or percentages', async () => {
  const user = userEvent.setup();
  setup();
  const selector = screen.getByRole('combobox', { name: 'Display currency' });
  expect(selector).toHaveValue('INR');
  expect(screen.getAllByText('₹1.25 INR')).toHaveLength(2);

  const currencies = [
    ['USD', '$1.25 USD'], ['EUR', '€1.25 EUR'], ['GBP', '£1.25 GBP'],
    ['JPY', '¥1.25 JPY'], ['CAD', 'C$1.25 CAD'], ['AUD', 'A$1.25 AUD'], ['INR', '₹1.25 INR'],
  ] as const;
  for (const [code, formattedAmount] of currencies) {
    await user.selectOptions(selector, code);
    expect(selector).toHaveValue(code);
    expect(screen.getAllByText(formattedAmount)).toHaveLength(2);
    expect(localStorage.getItem('tokentrim:display-currency')).toBe(code);
  }

  await user.click(screen.getByRole('button', { name: 'Compare All Supported LLMs' }));
  const comparison = screen.getByRole('table');
  expect(comparison).toHaveTextContent('40.0%');
  await user.selectOptions(selector, 'USD');
  expect(comparison).toHaveTextContent('40.0%');
  expect(comparison).toHaveTextContent('$0.0030 USD');
  expect(comparison).toHaveTextContent('$0.0018 USD');
});
