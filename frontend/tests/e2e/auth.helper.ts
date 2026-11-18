import { expect, Page } from '@playwright/test';

export async function signIn(page: Page) {
  await page.route(/\/auth\/login(?:\?.*)?$/, (route) => route.fulfill({ json: { access_token: 'playwright-session-token' } }));
  await page.route(/\/auth\/me(?:\?.*)?$/, (route) => route.fulfill({ json: { full_name: 'Demo User', email: 'demo@example.com' } }));
  await page.route('**/history**', (route) => ['xhr', 'fetch'].includes(route.request().resourceType())
    ? route.fulfill({ json: [] }) : route.continue());
  await page.route('**/dashboard/**', (route) => {
    if (!['xhr', 'fetch'].includes(route.request().resourceType())) return route.continue();
    const url = route.request().url();
    if (url.includes('/dashboard/overview')) return route.fulfill({ json: { total_tokens: 0, total_cost: 0, total_prompts: 0, total_savings: 0, average_reduction: 0 } });
    if (url.includes('/dashboard/token-savings')) return route.fulfill({ json: { total_tokens_saved: 0 } });
    return route.fulfill({ json: [] });
  });
  await page.goto('/');
  await page.getByRole('link', { name: 'Login' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Email').fill('demo@example.com');
  await dialog.getByLabel('Password').fill('password123');
  await dialog.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/dashboard/);
}
