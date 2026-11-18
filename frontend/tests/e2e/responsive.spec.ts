import { test, expect } from '@playwright/test';
import { signIn } from './auth.helper';
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
    await expect(page.getByRole('complementary', { name: 'Sidebar' })).toHaveCSS('width', '0px');
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
});

test('questionnaire stays within desktop, tablet, and narrow mobile viewports', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'questionnaire-audit-token');
    localStorage.setItem('user', JSON.stringify({ name: 'Viewport audit', email: 'audit@example.com' }));
  });
  await page.route('**/history**', route => ['xhr', 'fetch'].includes(route.request().resourceType())
    ? route.fulfill({ status: 200, json: [] }) : route.continue());
  await page.route('**/projects*', async route => {
    if (!['xhr', 'fetch'].includes(route.request().resourceType())) return route.continue();
    if (route.request().method() === 'GET') return route.fulfill({ status: 200, json: [] });
    return route.fulfill({ status: 200, json: { id: 42, name: 'Viewport audit' } });
  });

  for (const viewport of [
    { width: 1440, height: 900 }, { width: 768, height: 1024 },
    { width: 390, height: 844 }, { width: 320, height: 740 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
    await page.getByRole('button', { name: 'Create project' }).click();
    const dialog = page.getByRole('dialog', { name: 'Create a project' });
    const checkLayout = async (controls = ['Previous', 'Continue']) => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
      expect(await dialog.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(false);
      for (const label of controls) {
        const box = await dialog.getByRole('button', { name: label }).boundingBox();
        expect(box).not.toBeNull();
        expect(box!.height).toBeGreaterThanOrEqual(44);
        expect(box!.x).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width);
      }
    };
    await checkLayout();
    await dialog.getByLabel('Project name').fill('Viewport audit');
    await dialog.getByRole('button', { name: 'Continue' }).click();
    await dialog.getByRole('button', { name: 'Mobile Application' }).click();
    await dialog.getByRole('button', { name: 'Android', exact: true }).click();
    await dialog.getByRole('button', { name: 'iOS', exact: true }).click();
    await checkLayout();
    await dialog.getByRole('button', { name: 'Continue' }).click();
    await dialog.getByRole('button', { name: 'Cross-platform' }).click();
    await dialog.getByRole('button', { name: 'Next.js' }).click();
    await dialog.getByRole('button', { name: /^No$/ }).click();
    await dialog.getByRole('button', { name: 'Mobile devices' }).click();
    await checkLayout();
    await dialog.getByRole('button', { name: 'Skip' }).click();
    await expect(dialog.getByRole('heading', { name: 'Review your project requirements' })).toBeVisible();
    await checkLayout(['Previous', 'Submit requirements']);
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await page.evaluate(() => localStorage.removeItem('tokentrim:project-questionnaire:draft'));
  }
});
