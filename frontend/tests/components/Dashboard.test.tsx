import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '@/pages/dashboard';
const TITLES = ['Token usage over time', 'Cost over time', 'Cost by model', 'Token usage by model API', 'Usage by project', 'Savings over time'];
describe('dashboard', () => {
  it('renders metrics and all charts', async () => {
    render(<Dashboard />);
    expect(await screen.findByText('Total tokens')).toBeInTheDocument();
    TITLES.forEach((t) => expect(screen.getByRole('img', { name: `${t} chart` })).toBeInTheDocument());
  });
  it('changes range with the filter and shows date pickers for Custom', async () => {
    const user = userEvent.setup(); render(<Dashboard />);
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
