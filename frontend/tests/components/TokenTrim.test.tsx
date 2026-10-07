import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TokenTrimPage from '@/pages/index';
jest.mock('next/router', () => ({ useRouter: () => ({ query: {}, pathname: '/', push: jest.fn(), replace: jest.fn() }) }));
describe('Token Trim page', () => {
  it('shows validation errors on empty submit', async () => {
    const user = userEvent.setup(); render(<TokenTrimPage />);
    await user.click(screen.getByRole('button', { name: 'Analyze prompt' }));
    expect(screen.getByText('Enter a prompt to analyze.')).toBeInTheDocument();
    expect(screen.getByText('Select a model.')).toBeInTheDocument();
  });
  it('submits, shows loading, then renders results', async () => {
    const user = userEvent.setup(); render(<TokenTrimPage />);
    await user.type(screen.getByLabelText('Original prompt'), 'Please summarize the following document very clearly.');
    await screen.findByRole('option', { name: 'gpt-4o' });
    await user.selectOptions(screen.getByLabelText('Model'), 'gpt-4o');
    await user.click(screen.getByRole('button', { name: 'Analyze prompt' }));
    expect(await screen.findByText('Analyzing prompt...')).toBeInTheDocument();
    expect(await screen.findByText('Analysis completed.', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('Detected issues')).toBeInTheDocument();
    expect(screen.getByText('Tokens saved')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Copy optimized prompt' }));
    expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument();
  });
});
