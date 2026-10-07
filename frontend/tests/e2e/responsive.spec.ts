import { test, expect } from '@playwright/test';
import { signIn } from './journey.spec';
test('layout adapts to viewport', async ({ page, isMobile }) => {
  await signIn(page);
  if (isMobile) {
    await page.getByRole('button', { name: 'Menu' }).click();
    await expect(page.getByRole('link', { name: 'LLM Plans' })).toBeVisible();
  } else {
    await expect(page.getByRole('button', { name: 'Menu' })).toBeHidden();
    const nav = page.getByRole('navigation', { name: 'Main' });
    await expect(nav).toBeVisible();
    await page.getByRole('button', { name: 'Toggle sidebar' }).click();
    await expect(nav).toBeHidden();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
});
