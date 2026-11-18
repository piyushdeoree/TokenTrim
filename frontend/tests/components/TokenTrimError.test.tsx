import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TokenTrimPage from '@/pages/index';
import { ProviderProvider } from '@/context/ProviderContext';
jest.mock('@/context/AuthContext', () => ({ useAuth: () => ({ user: { id: 1 }, ready: true }) }));
jest.mock('@/hooks/useModelPricing', () => ({ useModelPricing: () => ({ state: { status: 'success', data: [{ model: 'gpt-4o', provider: 'OpenAI' }] } }) }));
jest.mock('next/router', () => ({ useRouter: () => ({ query: {}, pathname: '/', push: jest.fn(), replace: jest.fn() }) }));
jest.mock('@/services/promptService', () => ({ analyzePrompt: jest.fn().mockRejectedValue(new Error('boom')) }));
it('shows an error message when the API fails', async () => {
  const user = userEvent.setup(); render(<ProviderProvider><TokenTrimPage /></ProviderProvider>);
  await user.type(screen.getByLabelText('Original prompt'), 'Some prompt');
  await screen.findByRole('option', { name: 'gpt-4o' });
  await user.selectOptions(screen.getByLabelText('Model'), 'gpt-4o');
  await user.click(screen.getByRole('button', { name: 'Analyze prompt' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to analyze prompt. Please try again.');
});
