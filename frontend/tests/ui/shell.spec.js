import { test, expect } from '@playwright/test';

for (const width of [1440, 390]) {
  test(`login unchanged ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.route('**/api/v1/auth/me', route => route.fulfill({ status: 401, json: { detail: 'Login required' } }));
    await page.route('**/api/v1/auth/demo-accounts', route => route.fulfill({ json: { enabled: false, accounts: [] } }));
    // External fonts are blocked for a deterministic offline baseline, both before and after port.
    await page.route('https://fonts.googleapis.com/**', route => route.abort());
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Chào mừng trở lại' })).toBeVisible();
    await expect(page).toHaveScreenshot(`login-${width}.png`, { animations: 'disabled', maxDiffPixels: 1500 });
  });
}
