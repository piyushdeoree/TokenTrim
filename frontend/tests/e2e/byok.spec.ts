import { expect, test } from '@playwright/test';

test('provider management and optimized prompt demo work on desktop and mobile', async ({ page, isMobile }) => {
  const fakeKey = 'demo-anthropic-key-1234';
  const consoleLines: string[] = [];
  page.on('console', (message) => consoleLines.push(message.text()));
  await page.addInitScript(() => {
    localStorage.setItem('token', 'frontend-byok-test-token');
    localStorage.setItem('user', JSON.stringify({ id: 1, name: 'BYOK test', email: 'byok@example.test' }));
  });
  await page.route('**/models/pricing', (route) => route.fulfill({ json: [{ model: 'gpt-4o', provider: 'OpenAI', input_price_per_1k: 0.01, output_price_per_1k: 0.02 }] }));
  await page.route('**/models', (route) => route.fulfill({ json: [{ name: 'gpt-4o', context_window: 128000 }] }));
  await page.route('**/history**', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/analyze-prompt', (route) => {
    expect(route.request().headers().authorization).toBe('Bearer frontend-byok-test-token');
    return route.fulfill({ json: {
    prompt_id: 77, original_tokens: 12, optimized_tokens: 8, tokens_saved: 4, reduction_percentage: 33.3,
    predicted_output_tokens: 10, estimated_cost: 0.0012, potential_saving: 0.0008,
    issues: [], suggestions: [], optimized_prompt: 'Optimized text: use concise bullet points.',
    } });
  });

  await page.goto('/providers');
  await expect(page.getByRole('heading', { name: 'Provider connections' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'OpenAI' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Google Gemini' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Anthropic Claude' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await page.getByRole('button', { name: 'Connect' }).nth(2).click();
  const dialog = page.getByRole('dialog', { name: 'Connect Anthropic Claude' });
  await dialog.getByRole('textbox', { name: 'API key' }).fill(fakeKey);
  await dialog.getByRole('button', { name: 'Connect provider' }).click();
  await expect(page.getByText('Key: ••••••••1234')).toBeVisible();
  await expect(page.locator('body')).not.toContainText(fakeKey);
  expect(consoleLines.join('\n')).not.toContain(fakeKey);
  await page.getByRole('button', { name: 'Test connection' }).click();
  await expect(page.getByText(/Demo connection is ready/)).toBeVisible();

  if (isMobile) await page.getByRole('button', { name: 'Menu' }).click();
  await page.getByRole('link', { name: 'Token Trim', exact: true }).click();
  await page.getByLabel('Original prompt').fill('Summarize this information clearly.');
  await page.getByLabel('Model').selectOption('gpt-4o');
  await page.getByRole('button', { name: 'Analyze prompt' }).click();
  await expect(page.getByText('Analysis completed.')).toBeVisible();
  await expect(page.getByText('Optimized text: use concise bullet points.')).toBeVisible();
  await page.getByLabel('Execution model').selectOption('claude-3-5-haiku-latest');
  await page.getByRole('button', { name: 'Run Optimized Prompt' }).click();
  await expect(page.getByText(/Demo response · not from an LLM/)).toBeVisible();
  await expect(page.getByText(/usage and actual cost are unavailable/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
