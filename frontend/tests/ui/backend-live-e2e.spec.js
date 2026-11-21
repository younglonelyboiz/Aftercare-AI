import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const patientId = 'BN-2026-ASTHMA-01';
const evidenceDir = path.resolve(process.cwd(), '../Evidence/W08/demo-videos');
const rawVideoDir = path.resolve(process.cwd(), 'test-results/backend-live-video');

const pause = (page, ms) => page.waitForTimeout(ms);

async function signIn(page, role, slow = false) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Chào mừng trở lại' })).toBeVisible();
  if (slow) await pause(page, 2500);
  await page.getByRole('button', { name: role === 'patient' ? 'Bệnh nhân' : 'Điều dưỡng' }).click();
  if (slow) await pause(page, 1500);
  await page.getByRole('button', { name: role === 'patient' ? 'Nguyễn Văn An' : 'Điều dưỡng W08' }).click();
  if (slow) await pause(page, 3500);
}

test('full live scenario video: patient reports red flag and nurse resolves the alert', async ({ browser }) => {
  fs.mkdirSync(rawVideoDir, { recursive: true });
  const watcherContext = await browser.newContext();
  const watcherPage = await watcherContext.newPage();
  let demoContext;
  let demoPage;
  const nurseEvents = [];
  watcherPage.on('websocket', socket => {
    if (socket.url().includes('/escalations/ws/nurse-alerts')) {
      socket.on('framesent', frame => nurseEvents.push(`sent:${frame.payload}`));
      socket.on('framereceived', frame => nurseEvents.push(`received:${frame.payload}`));
    }
  });

  try {
    await signIn(watcherPage, 'nurse');
    await expect.poll(() => nurseEvents.some(event => event.includes('CONNECTED'))).toBeTruthy();
    await expect(watcherPage.getByText('Trung tâm Điều dưỡng')).toBeVisible({ timeout: 20000 });

    demoContext = await browser.newContext({ recordVideo: { dir: rawVideoDir } });
    demoPage = await demoContext.newPage();
    await signIn(demoPage, 'patient', true);
    await expect(demoPage.locator('#patient-overview-section')).toBeVisible({ timeout: 20000 });
    await pause(demoPage, 5000);
    await demoPage.getByRole('button', { name: 'Hỏi trợ lý HOPI' }).click();
    await expect(demoPage.locator('.chat-popup')).toBeVisible();
    await pause(demoPage, 2500);
    await demoPage.getByRole('textbox', { name: 'Tin nhắn cho trợ lý' }).pressSequentially('Tôi khó thở dữ dội và môi tím tái, cần trợ giúp ngay.', { delay: 55 });
    await demoPage.getByRole('button', { name: 'Gửi tin nhắn' }).click();
    await expect(demoPage.getByRole('link', { name: 'Gọi 115' })).toBeVisible({ timeout: 15000 });
    await pause(demoPage, 7000);

    await expect(watcherPage.getByText('Nguồn: Chatbot', { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(watcherPage.getByText('Nguyễn Văn An (28t)').first()).toBeVisible();
    await expect.poll(() => nurseEvents.some(event => event.includes('NEW_ALERT_TICKET'))).toBeTruthy();

    await pause(demoPage, 3000);
    await demoPage.getByRole('button', { name: 'Đăng xuất' }).click();
    await expect(demoPage.getByRole('heading', { name: 'Chào mừng trở lại' })).toBeVisible();
    await pause(demoPage, 4000);
    await signIn(demoPage, 'nurse', true);
    await expect(demoPage.getByText('Nguồn: Chatbot', { exact: true })).toBeVisible({ timeout: 15000 });
    await expect(demoPage.getByText('Nguyễn Văn An (28t)').first()).toBeVisible();
    await pause(demoPage, 10000);

    await demoPage.getByRole('button', { name: 'Tiếp Nhận Ca' }).click();
    await expect(demoPage.getByText('Đã Tiếp Nhận Ca')).toBeVisible({ timeout: 10000 });
    await expect.poll(() => nurseEvents.some(event => event.includes('TICKET_ACKNOWLEDGED'))).toBeTruthy();
    await pause(demoPage, 5000);

    await demoPage.getByRole('button', { name: 'Xử Lý & Ký Biên Bản' }).click();
    await expect(demoPage.getByRole('heading', { name: 'Biên Bản Xử Lý Cảnh Báo Lâm Sàng' })).toBeVisible();
    await pause(demoPage, 8000);
    await demoPage.locator('.modal-card-escalation textarea.textarea-esc').pressSequentially('Đã liên hệ người bệnh, hướng dẫn gọi 115; ghi nhận đã chuyển cấp cứu.', { delay: 45 });
    await pause(demoPage, 7000);
    await demoPage.getByRole('button', { name: 'Ký Biên Bản & Hoàn Tất Xử Lý' }).click();
    await expect(demoPage.getByText('Đã Đóng Ca Can Thiệp Thành Công')).toBeVisible({ timeout: 12000 });
    await pause(demoPage, 8000);
    await expect.poll(() => nurseEvents.some(event => event.includes('TICKET_RESOLVED'))).toBeTruthy();

    const apiState = await demoPage.evaluate(async () => {
      const response = await fetch('http://127.0.0.1:8011/api/v1/escalations/tickets/history', { credentials: 'include' });
      return response.json();
    });
    const resolvedTicket = apiState.find(ticket => ticket.patient_id === patientId && ticket.alert_type === 'CHAT_RED_FLAG_DETECTION');
    expect(resolvedTicket?.status).toBe('RESOLVED');
    expect(resolvedTicket?.resolution_notes).toContain('gọi 115');
  } finally {
    const video = demoPage?.video();
    await demoContext?.close().catch(() => {});
    await watcherContext.close().catch(() => {});
    if (video) {
      fs.mkdirSync(evidenceDir, { recursive: true });
      await video.saveAs(path.join(evidenceDir, '04-live-backend-patient-to-nurse.webm'));
    }
  }
});
