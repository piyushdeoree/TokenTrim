import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TokenTrimPage from '@/pages/index';
import { ProviderProvider } from '@/context/ProviderContext';
jest.mock('@/context/AuthContext', () => ({ useAuth: () => ({ user: { id: 1 }, ready: true }) }));
jest.mock('@/hooks/useModelPricing', () => ({ useModelPricing: () => ({ state: { status: 'success', data: [{ model: 'gpt-4o', provider: 'OpenAI' }] } }) }));
jest.mock('@/services/promptService', () => ({ analyzePrompt: jest.fn().mockImplementation(() => new Promise((resolve) => setTimeout(() => resolve({ prompt_id: 1, original_tokens: 10, optimized_tokens: 8, tokens_saved: 2, reduction_percentage: 20, predicted_output_tokens: 5, estimated_cost: 0.01, potential_saving: 0.02, issues: [], suggestions: [], optimized_prompt: 'Optimized prompt' }), 80))) }));
jest.mock('next/router', () => ({ useRouter: () => ({ query: {}, pathname: '/', push: jest.fn(), replace: jest.fn() }) }));
const renderPage = () => render(<ProviderProvider><TokenTrimPage /></ProviderProvider>);
describe('Token Trim page', () => {
  it('shows validation errors on empty submit', async () => {
    const user = userEvent.setup(); renderPage();
    await user.click(screen.getByRole('button', { name: 'Analyze prompt' }));
    expect(screen.getByText('Enter a prompt to analyze.')).toBeInTheDocument();
    expect(screen.getByText('Select a model.')).toBeInTheDocument();
  });
  it('submits, shows loading, then renders results', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: jest.fn().mockResolvedValue(undefined) } });
    const user = userEvent.setup(); renderPage();
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

  it('falls back to manual copying and explains when clipboard access is denied', async () => {
    const user = userEvent.setup();
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: jest.fn().mockRejectedValue(new Error('Clipboard unavailable')) } });
    Object.defineProperty(document, 'execCommand', { configurable: true, value: jest.fn().mockReturnValue(false) });
    renderPage();
    await user.type(screen.getByLabelText('Original prompt'), 'Please summarize this content clearly.');
    await screen.findByRole('option', { name: 'gpt-4o' });
    await user.selectOptions(screen.getByLabelText('Model'), 'gpt-4o');
    await user.click(screen.getByRole('button', { name: 'Analyze prompt' }));
    await screen.findByText('Analysis completed.');
    await user.click(screen.getByRole('button', { name: 'Copy optimized prompt' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to copy automatically. Select and copy the text manually.');
  });
});
