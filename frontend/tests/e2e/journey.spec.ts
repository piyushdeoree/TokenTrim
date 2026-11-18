import { test, expect } from '@playwright/test';
import { signIn } from './auth.helper';
test('home modal login → token trim → analyze → save', async ({ page }) => {
  await signIn(page);
  await expect(page.getByText('Total tokens')).toBeVisible();
  await page.goto('/');
  await expect(page.getByRole('img', { name: 'TokenTrim logo' })).toBeVisible();
  await page.getByLabel('Original prompt').fill('Please summarize the following document clearly and concisely.');
  await expect(page.getByRole('option', { name: 'gpt-4o', exact: true })).toBeAttached();
  await page.getByLabel('Model').selectOption('gpt-4o');
  await page.getByRole('button', { name: 'Analyze prompt' }).click();
  await expect(page.getByText('Analysis completed.')).toBeVisible();
  await page.getByRole('button', { name: 'Save analysis' }).click();
  await page.getByLabel('Project').selectOption({ index: 1 });
  await page.getByRole('dialog').getByRole('button', { name: 'Save analysis' }).click();
  await expect(page.getByText('Analysis saved.')).toBeVisible();
});
test('protected pages send logged-out users to the Home login modal', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/auth=login/);
  await expect(page.getByRole('dialog', { name: 'Sign in to TokenTrim' })).toBeVisible();
});
test('theme toggle persists across reload', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Switch to dark mode' }).click();
  await expect(page.locator('html')).toHaveClass(/dark/);
  await page.reload(); await expect(page.locator('html')).toHaveClass(/dark/);
});
