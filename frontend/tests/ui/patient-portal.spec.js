import { test, expect } from '@playwright/test';

const patientId = 'BN-2026-ASTHMA-01';

async function signInPatient(page) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Chào mừng trở lại' })).toBeVisible();
  await page.getByRole('button', { name: 'Bệnh nhân' }).click();
  await page.getByRole('button', { name: 'Nguyễn Văn An' }).click();
  await expect(page.locator('#patient-overview-section')).toBeVisible();
}

test('patient check-in and HOPI use the live backend', async ({ page }) => {
  const unexpectedFailures = [];
  page.on('response', response => {
    if (response.url().includes('/api/v1/') && response.status() >= 500) {
      unexpectedFailures.push(`${response.status()} ${response.url()}`);
    }
  });
  await signInPatient(page);
  await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();
  await expect(page.locator('#patient-checkin-section')).toBeVisible();
  await page.locator('#pef-number-input').fill('465');
  const checkinResponse = page.waitForResponse(response =>
    response.url().endsWith('/api/v1/care-tracker/checkin/') && response.request().method() === 'POST'
  );
  const dialogPromise = page.waitForEvent('dialog');
  await page.getByRole('button', { name: 'Lưu đánh giá hôm nay' }).click();
  const dialog = await dialogPromise;
  expect(dialog.message()).toContain('Đã lưu Check-in vào cơ sở dữ liệu');
  await dialog.accept();
  const savedCheckin = await checkinResponse;
  expect(savedCheckin.ok()).toBeTruthy();
  const checkin = await savedCheckin.json();
  expect(checkin.action_zone).toBe('GREEN');
  const history = await page.evaluate(async id => {
    const response = await fetch(`http://127.0.0.1:8011/api/v1/care-tracker/checkin/history/${id}`, { credentials: 'include' });
    if (!response.ok) throw new Error(`Check-in history ${response.status}`);
    return response.json();
  }, patientId);
  expect(history.some(row => row.id === checkin.checkin_id && row.pef_value === 465)).toBeTruthy();

  await page.getByRole('button', { name: 'Hỏi trợ lý HOPI' }).click();
  await expect(page.locator('.chat-popup')).toBeVisible();
  const chatResponse = page.waitForResponse(response =>
    response.url().endsWith('/api/v1/chat/chat') && response.request().method() === 'POST'
  );
  await page.getByRole('textbox', { name: 'Tin nhắn cho trợ lý' }).fill('Tôi khó thở dữ dội và môi tím tái, cần trợ giúp ngay.');
  await page.getByRole('button', { name: 'Gửi tin nhắn' }).click();
  const replied = await chatResponse;
  expect(replied.ok()).toBeTruthy();
  expect((await replied.json()).safety_status).toBe('RED_ZONE');
  await expect(page.getByRole('link', { name: 'Gọi 115' })).toBeVisible();
  expect(unexpectedFailures).toEqual([]);
});
