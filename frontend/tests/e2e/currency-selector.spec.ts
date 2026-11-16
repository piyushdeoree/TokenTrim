import { test, expect } from '@playwright/test';

test('currency selection changes labels only and fits supported viewport widths', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'currency-test-token');
    localStorage.setItem('user', JSON.stringify({ id: 1, name: 'Currency test', email: 'currency@example.com' }));
  });
  await page.route('http://127.0.0.1:8000/dashboard/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/overview')) return route.fulfill({ status: 200, json: { total_tokens: 100, total_cost: 1.25, total_prompts: 2, total_savings: 0.25, average_reduction: 25 } });
    if (path.endsWith('/token-savings')) return route.fulfill({ status: 200, json: { total_tokens_saved: 10 } });
    if (path.endsWith('/daily-usage')) return route.fulfill({ status: 200, json: [{ date: '2026-11-16', tokens: 20, cost: 1.25, requests: 2, saved: 5 }] });
    if (path.endsWith('/cost-by-model')) return route.fulfill({ status: 200, json: [{ model: 'gpt-4o', tokens: 20, cost: 1.25, requests: 2 }] });
    if (path.endsWith('/cost-by-project')) return route.fulfill({ status: 200, json: [{ project: 'Test project', tokens: 20, cost: 1.25, requests: 2 }] });
    return route.fulfill({ status: 404, json: { detail: 'Not found' } });
  });

  const viewports = [{ width: 320, height: 740 }, { width: 390, height: 844 }, { width: 768, height: 1024 }, { width: 1440, height: 900 }];
  for (const [index, viewport] of viewports.entries()) {
    await page.setViewportSize(viewport);
    await page.goto('/dashboard');
    const selector = page.getByRole('combobox', { name: 'Display currency' });
    if (index > 0) await selector.selectOption('INR');
    await expect(selector).toBeVisible();
    await expect(selector).toHaveValue('INR');
    await expect(page.getByText('₹1.25 INR', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('25.0%')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);

    await selector.selectOption('USD');
    await expect(page.getByText('$1.25 USD', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('25.0%')).toBeVisible();
    if (index === viewports.length - 1) {
      await page.reload();
      await expect(page.getByRole('combobox', { name: 'Display currency' })).toHaveValue('USD');
      await expect(page.getByText('$1.25 USD', { exact: true }).first()).toBeVisible();
    }
  }
});
