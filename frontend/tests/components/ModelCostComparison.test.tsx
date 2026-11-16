import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ModelCostComparison } from '@/components/token-trim/ModelCostComparison';

describe('ModelCostComparison', () => {
  it('starts collapsed and preserves its contents when toggled', async () => {
    const user = userEvent.setup();
    render(<ModelCostComparison />);

    expect(screen.queryByText('Illustrative comparison — live model pricing is not connected yet.')).not.toBeInTheDocument();
    const toggle = screen.getByRole('button', { name: 'Compare All Supported LLMs' });
    await user.click(toggle);
    expect(screen.getByText('Illustrative comparison — live model pricing is not connected yet.')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Hide comparison' }));
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Compare All Supported LLMs' }));
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('filters providers and sorts the visible comparison rows', async () => {
    const user = userEvent.setup();
    render(<ModelCostComparison />);
    await user.click(screen.getByRole('button', { name: 'Compare All Supported LLMs' }));

    const providerFilter = screen.getByRole('combobox', { name: 'Filter by provider' });
    await user.selectOptions(providerFilter, 'Google');
    expect(screen.getByRole('row', { name: /Google Gemini 1.5 Pro/ })).toBeInTheDocument();
    expect(screen.queryByRole('row', { name: /OpenAI GPT-4o/ })).not.toBeInTheDocument();
    expect(screen.getByText('Models compared').parentElement).toHaveTextContent('1');

    await user.selectOptions(providerFilter, 'all');
    const sort = screen.getByRole('combobox', { name: 'Sort comparisons' });
    await user.selectOptions(sort, 'savingsPercent');
    const modelCells = within(screen.getByRole('table')).getAllByRole('row').slice(1)
      .map((row) => within(row).getAllByRole('cell')[1].textContent);
    expect(modelCells[0]).toContain('GPT-4o');
    expect(modelCells[1]).toContain('Gemini 1.5 Pro');
  });
});
