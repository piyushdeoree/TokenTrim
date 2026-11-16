import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '@/pages/dashboard';
import { CurrencyProvider } from '@/context/CurrencyContext';
jest.mock('@/hooks/useDashboardData', () => ({ useDashboardData: () => ({
  state: { status: 'success', data: {
    totals: { tokens: 100, cost: 1.25, prompts: 2, saved: 10, potential: 0.25, avg_reduction: 25 },
    usage: [{ day: '2026-11-16', tokens: 100, cost: 1.25, saved: 10 }],
    byModel: [{ name: 'gpt-4o', cost: 1.25 }], byModelTokens: [{ name: 'gpt-4o', tokens: 100 }], byProject: [{ name: 'Sample project', tokens: 100 }],
  } }, reload: jest.fn(),
}) }));
const TITLES = ['Token usage over time', 'Cost over time', 'Cost by model', 'Token usage by model API', 'Usage by project', 'Savings over time'];
const renderDashboard = () => render(<CurrencyProvider><Dashboard /></CurrencyProvider>);
describe('dashboard', () => {
  it('renders metrics and all charts', async () => {
    renderDashboard();
    expect(await screen.findByText('Total tokens')).toBeInTheDocument();
    TITLES.forEach((t) => expect(screen.getByRole('img', { name: `${t} chart` })).toBeInTheDocument());
    expect(screen.getByRole('combobox', { name: 'Display currency' })).toHaveValue('INR');
    expect(screen.getByText('₹1.25 INR')).toBeInTheDocument();
  });
  it('changes range with the filter and shows date pickers for Custom', async () => {
    const user = userEvent.setup(); renderDashboard();
    await screen.findByText('Total tokens');
    expect(screen.getByRole('button', { name: 'Weekly' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: 'Monthly' }));
    expect(screen.getByRole('button', { name: 'Monthly' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: 'Custom' }));
    expect(screen.getByLabelText('From')).toBeInTheDocument();
    expect(screen.getByLabelText('To')).toBeInTheDocument();
    expect(await screen.findByText('Total tokens')).toBeInTheDocument();
  });
});
