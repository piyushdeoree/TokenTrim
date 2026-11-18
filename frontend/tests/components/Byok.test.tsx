import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProviderProvider } from '@/context/ProviderContext';
import { ProviderCard } from '@/components/providers/ProviderCard';
import { PromptExecutionPanel } from '@/components/execution/PromptExecutionPanel';
import { ExecutionResult } from '@/components/execution/ExecutionResult';
import { connectProvider, disconnectProvider } from '@/services/byok/providerCredentialService';
import type { PromptExecutionResult } from '@/types/execution';
import { PROVIDERS } from '@/services/byok/providerConfig';
import { configureByokAdapter, getByokAdapter } from '@/services/byok/adapter';
import { createDemoAdapter } from '@/services/byok/demoAdapter';
import { ProviderConnectionModal } from '@/components/providers/ProviderConnectionModal';
import { sanitizeProviderConnection } from '@/services/byok/errors';
import { sanitizeExecutionResult } from '@/services/byok/executionUsageService';

beforeEach(() => { configureByokAdapter(createDemoAdapter()); });
afterEach(async () => { await Promise.all(PROVIDERS.map(({ id }) => disconnectProvider(id))); jest.restoreAllMocks(); });

it.each(PROVIDERS)('$name has a working connect card and connection status', async (provider) => {
  const user = userEvent.setup();
  render(<ProviderProvider><ProviderCard provider={provider} /></ProviderProvider>);
  await user.click(await screen.findByRole('button', { name: 'Connect' }));
  await user.type(screen.getByLabelText('API key'), 'demo-key-1234');
  await user.click(screen.getByRole('button', { name: 'Connect provider' }));
  expect(await screen.findByText('Connected')).toBeInTheDocument();
  expect(screen.getByText('Key: ••••••••1234')).toBeInTheDocument();
});

it('validates, connects, tests and confirms disconnect without displaying the submitted key', async () => {
  const user = userEvent.setup();
  render(<ProviderProvider><ProviderCard provider={PROVIDERS[0]} /></ProviderProvider>);
  await user.click(await screen.findByRole('button', { name: 'Connect' }));
  const key = screen.getByLabelText('API key');
  expect(key).toHaveAttribute('type', 'password');
  await user.click(screen.getByRole('checkbox', { name: 'Show API key' }));
  expect(key).toHaveAttribute('type', 'text');
  await user.click(screen.getByRole('checkbox', { name: 'Show API key' }));
  await user.type(key, 'short');
  await user.click(screen.getByRole('button', { name: 'Connect provider' }));
  expect(await screen.findByText('Enter an API key with at least 8 characters.')).toBeInTheDocument();
  await user.clear(key);
  await user.type(key, 'sk-demo-1234');
  await user.click(screen.getByRole('button', { name: 'Connect provider' }));
  expect(await screen.findByText('Key: ••••••••1234')).toBeInTheDocument();
  expect(screen.queryByDisplayValue('sk-demo-1234')).not.toBeInTheDocument();
  const storedValues = [window.localStorage, window.sessionStorage].flatMap((storage) => Array.from({ length: storage.length }, (_, index) => storage.getItem(storage.key(index) ?? '') ?? '')).join(' ');
  expect(storedValues).not.toContain('sk-demo-1234');
  await user.click(screen.getByRole('button', { name: 'Test connection' }));
  expect(await screen.findByText(/Demo connection is ready/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Replace key' }));
  await user.type(screen.getByLabelText('API key'), 'sk-demo-6789');
  await user.click(screen.getByRole('button', { name: 'Connect provider' }));
  expect(await screen.findByText('Key: ••••••••6789')).toBeInTheDocument();
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  await user.click(screen.getByRole('button', { name: 'Disconnect' }));
  await waitFor(() => expect(screen.getByText('Disconnected')).toBeInTheDocument());
});

it('reports demo key rejection in the connection dialog', async () => {
  const user = userEvent.setup();
  render(<ProviderProvider><ProviderCard provider={PROVIDERS[0]} /></ProviderProvider>);
  await user.click(await screen.findByRole('button', { name: 'Connect' }));
  await user.type(screen.getByLabelText('API key'), 'invalid-demo-key');
  await user.click(screen.getByRole('button', { name: 'Connect provider' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Demo adapter rejected this key');
});

it('redacts a submitted key if a future backend error echoes it', async () => {
  const user = userEvent.setup();
  const secret = 'sk-demo-secret-key-987654';
  const onConnect = jest.fn().mockRejectedValue(new Error(`Rejected credential ${secret}`));
  render(<ProviderConnectionModal provider={PROVIDERS[0]} onClose={jest.fn()} onConnect={onConnect} />);
  await user.type(screen.getByLabelText('API key'), secret);
  await user.click(screen.getByRole('button', { name: 'Connect provider' }));
  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('[redacted]');
  expect(alert).not.toHaveTextContent(secret);
});

it('drops raw credential fields from provider connection responses', () => {
  const sanitized = sanitizeProviderConnection({ provider: 'openai', status: 'connected', api_key: 'sk-should-never-render', maskedKey: 'sk-should-never-render' });
  expect(sanitized).not.toHaveProperty('api_key');
  expect(sanitized).not.toHaveProperty('maskedKey');
});

it('shows the empty provider state when no connections exist', async () => {
  render(<ProviderProvider><PromptExecutionPanel optimizedPrompt="Be concise." /></ProviderProvider>);
  expect(await screen.findByText('No providers connected yet.')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Manage provider connections' })).toHaveAttribute('href', '/providers');
});

it('sanitizes secret-like values and invalid or missing usage values from execution responses', () => {
  const safe = sanitizeExecutionResult({
    id: 'ex-1', provider: 'gemini', model: 'gemini-flash', response: 'Output sk-proj-supersecretvalue123456789',
    usage: { inputTokens: 2, outputTokens: null, totalTokens: 'unknown', api_key: 'secret' }, actualCost: { amount: null },
    actualSavings: null, durationMs: -1, createdAt: 'not-a-date', api_key: 'never expose this',
  });
  expect(safe.response).not.toContain('sk-proj-supersecretvalue123456789');
  expect(safe.usage.totalTokens).toBeNull();
  expect(safe.actualCost.amount).toBeNull();
  expect(safe.durationMs).toBeNull();
  expect(safe.createdAt).toBeNull();
  expect(safe).not.toHaveProperty('api_key');
  expect(safe.usage).not.toHaveProperty('api_key');
});

it('runs only a labeled preview and renders missing usage as unavailable', async () => {
  const user = userEvent.setup();
  await connectProvider({ provider: 'openai', apiKey: 'sk-demo-1234' });
  await connectProvider({ provider: 'gemini', apiKey: 'gemini-demo-1234' });
  await connectProvider({ provider: 'anthropic', apiKey: 'claude-demo-1234' });
  const execute = jest.spyOn(getByokAdapter(), 'executePrompt');
  render(<ProviderProvider><PromptExecutionPanel optimizedPrompt="Be concise." estimatedCost={0.01} estimatedSaving={0.02} /></ProviderProvider>);
  await screen.findByRole('option', { name: 'GPT-4o · Demo' });
  await user.selectOptions(screen.getByLabelText('Provider'), 'anthropic');
  await screen.findByRole('option', { name: 'Claude 3.5 Sonnet · Demo' });
  await user.selectOptions(screen.getByLabelText('Execution model'), 'claude-3-5-haiku-latest');
  const runButton = screen.getByRole('button', { name: 'Run Optimized Prompt' });
  fireEvent.click(runButton);
  fireEvent.click(runButton);
  expect(runButton).toBeDisabled();
  expect(await screen.findByText(/Demo response · not from an LLM/)).toBeInTheDocument();
  expect(execute).toHaveBeenCalledTimes(1);
  expect(execute).toHaveBeenCalledWith({ prompt: 'Be concise.', provider: 'anthropic', model: 'claude-3-5-haiku-latest' });
  expect(screen.getByText(/No provider API was called, and its usage and actual cost are unavailable/)).toBeInTheDocument();
  expect(screen.getAllByText('Not available').length).toBeGreaterThanOrEqual(4);
  expect(screen.getByText('Estimated optimization cost')).toBeInTheDocument();
});

it('formats a tiny backend cost and keeps the execution status separate from estimates', () => {
  const result: PromptExecutionResult = { id: 'ex-1', provider: 'openai', model: 'gpt-4o', response: 'A response', usage: { inputTokens: 3, outputTokens: 4, totalTokens: 7 }, actualCost: { amount: 0.0000008, currency: 'USD' }, actualSavings: { amount: 0.0000012, currency: 'EUR' }, durationMs: 50, isDemo: false, createdAt: new Date().toISOString() };
  render(<ExecutionResult result={result} estimatedCost={0.1} estimatedSaving={0.02} />);
  expect(screen.getByText('A response')).toBeInTheDocument();
  expect(screen.getAllByText(/USD\s*0\.0000008/)).toHaveLength(2);
  expect(screen.getByText(/EUR\s*0\.0000012/)).toBeInTheDocument();
  expect(screen.getAllByText(/INR\s*0\.10/)).toHaveLength(1);
  expect(screen.getByText('7')).toBeInTheDocument();
});
