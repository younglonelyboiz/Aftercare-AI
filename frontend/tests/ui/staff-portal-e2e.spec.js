import { test, expect } from '@playwright/test';

test('nurse reviews, acknowledges, and resolves a patient alert', async ({ page }) => {
  let ticketStatus = 'OPEN';

  await page.route('**/api/v1/auth/me', route => route.fulfill({
    json: { id: 'nurse-1', username: 'nurse1', full_name: 'Điều dưỡng Lan', role: 'nurse', patient_id: null },
  }));
  await page.route('**/api/v1/patients/', route => route.fulfill({
    json: [{ patient_id: 'BN001', full_name: 'Nguyễn Văn An', age: 58, personal_best_pef: 500 }],
  }));
  await page.route('**/api/v1/care-tracker/nurse/patients-overview', route => route.fulfill({
    json: [{ patient_id: 'BN001', full_name: 'Nguyễn Văn An', action_zone: 'RED', today_checked_in: false }],
  }));
  await page.route('**/api/v1/care-tracker/care-plans/**', route => route.fulfill({
    json: { patient_id: 'BN001', personal_best_pef: 500, baseline_spo2: 98, doctor_notes: '', items: [] },
  }));
  await page.route('**/api/v1/care-tracker/checkin/history/**', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/escalations/tickets/active', route => route.fulfill({
    json: ticketStatus === 'RESOLVED' ? [] : [{
      id: 'ticket-e2e-1', patient_id: 'BN001', patient_name: 'Nguyễn Văn An',
      priority: 'P0_CRITICAL', alert_type: 'CHAT_RED_FLAG_DETECTION',
      trigger_reason: 'Bệnh nhân báo khó thở dữ dội, tím môi.',
      clinical_data: { source: 'CHAT' }, status: ticketStatus,
      created_at: new Date().toISOString(), escalation_latency_ms: 12,
    }],
  }));
  await page.route('**/api/v1/escalations/tickets/ticket-e2e-1/acknowledge', async route => {
    ticketStatus = 'ACKNOWLEDGED';
    await route.fulfill({ json: {
      id: 'ticket-e2e-1', patient_id: 'BN001', priority: 'P0_CRITICAL', status: ticketStatus,
      acknowledged_by: 'Điều dưỡng Lan', created_at: new Date().toISOString(),
    } });
  });
  await page.route('**/api/v1/escalations/tickets/ticket-e2e-1/resolve', async route => {
    ticketStatus = 'RESOLVED';
    await route.fulfill({ json: {
      id: 'ticket-e2e-1', patient_id: 'BN001', priority: 'P0_CRITICAL', status: ticketStatus,
      resolved_by: 'Điều dưỡng Lan', resolution_notes: route.request().postDataJSON().resolution_notes,
      created_at: new Date().toISOString(),
    } });
  });
  await page.routeWebSocket('**/escalations/ws/nurse-alerts', ws => {
    ws.onMessage(message => { if (message === 'ping') ws.send('pong'); });
    ws.send(JSON.stringify({ event: 'CONNECTED', message: 'connected' }));
  });

  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Trung Tâm Điều Dưỡng/i })).toBeVisible();
  await expect(page.locator('.live-escalation-banner')).toContainText('Bệnh nhân báo khó thở dữ dội');
  await expect(page.locator('.source-chatbot-badge')).toContainText('Nguồn: Chatbot');

  await page.getByRole('button', { name: /Tiếp Nhận Ca/i }).click();
  await expect(page.getByText('Đã Tiếp Nhận Ca')).toBeVisible();
  expect(ticketStatus).toBe('ACKNOWLEDGED');

  await page.getByRole('button', { name: /Xử Lý & Ký Biên Bản/i }).click();
  await expect(page.getByRole('heading', { name: 'Biên Bản Xử Lý Cảnh Báo Lâm Sàng' })).toBeVisible();
  await page.locator('.modal-body-escalation textarea').fill(
    'Đã gọi bệnh nhân, hướng dẫn gọi 115 và xác nhận người nhà đang hỗ trợ.'
  );
  await page.getByRole('button', { name: /Ký Biên Bản & Hoàn Tất Xử Lý/i }).click();
  await expect(page.getByText('Đã Đóng Ca Can Thiệp Thành Công')).toBeVisible();
  expect(ticketStatus).toBe('RESOLVED');
  await expect(page.locator('.live-escalation-banner')).toHaveCount(0);

});
