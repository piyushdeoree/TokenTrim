import { test, expect } from '@playwright/test';

const historyRows = Array.from({ length: 30 }, (_, index) => ({
  id: index + 1,
  created_at: new Date(Date.now() - index * 60_000).toISOString(),
  original_prompt: `Recent prompt ${index + 1}`,
  optimized_prompt: `Optimized prompt ${index + 1}`,
  model: 'gpt-4o',
  project: 'Sidebar verification',
  original_tokens: 20,
  optimized_tokens: 10,
  tokens_saved: 10,
  reduction_percentage: 50,
}));

test('Recent History toggles, persists, scrolls independently, and links to full history', async ({ page, isMobile }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'sidebar-test-token');
    localStorage.setItem('user', JSON.stringify({ id: 1, name: 'Sidebar test', email: 'sidebar@example.com' }));
    localStorage.setItem('recentHistoryExpanded', '1');
  });
  await page.route('http://127.0.0.1:8000/history**', (route) => route.fulfill({ status: 200, json: historyRows }));

  await page.goto('/about');
  if (isMobile) await page.getByRole('button', { name: 'Menu' }).click();

  const region = () => page.locator('section[aria-label="Recent history"]:visible').last();
  const toggle = () => region().getByRole('button', { name: 'View Recent History' });
  const list = () => region().locator('[id^="recent-history-list-"]');
  await expect(toggle()).toHaveAttribute('aria-expanded', 'true');
  await expect(list().getByText('Recent prompt 1', { exact: true })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Prompt History' })).toHaveCount(0);

  const dimensions = await list().evaluate((node) => {
    const element = node as HTMLElement;
    return {
      overflowY: getComputedStyle(element).overflowY,
      canScroll: element.scrollHeight > element.clientHeight,
      clientHeight: element.clientHeight,
    };
  });
  expect(dimensions.overflowY).toBe('auto');
  expect(dimensions.canScroll).toBe(true);
  expect(dimensions.clientHeight).toBeGreaterThan(0);
  await list().evaluate((node) => { (node as HTMLElement).scrollTop = 100; });
  await expect.poll(() => list().evaluate((node) => (node as HTMLElement).scrollTop)).toBeGreaterThan(0);
  expect(await list().evaluate((node) => node.parentElement?.scrollTop ?? 0)).toBe(0);

  await toggle().click();
  await expect(toggle()).toHaveAttribute('aria-expanded', 'false');
  expect(await page.evaluate(() => localStorage.getItem('recentHistoryExpanded'))).toBe('0');
  await toggle().click();
  await expect(toggle()).toHaveAttribute('aria-expanded', 'true');

  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Settings' }).click();
  await expect(page).toHaveURL(/settings/);
  if (isMobile) await page.getByRole('button', { name: 'Menu' }).click();
  await expect(toggle()).toHaveAttribute('aria-expanded', 'true');
  await page.reload();
  if (isMobile) await page.getByRole('button', { name: 'Menu' }).click();
  await expect(toggle()).toHaveAttribute('aria-expanded', 'true');

  await region().getByRole('link', { name: 'View full prompt history' }).click();
  await expect(page).toHaveURL(/\/history$/);
  await expect(page.getByRole('heading', { name: 'Prompt history' })).toBeVisible();
});
