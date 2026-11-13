import { test, expect } from '@playwright/test';

const SCREENSHOT_DIR = '../docs/design-handoff/screenshots';

function getVnDateOffset(daysAgo = 0) {
  const now = new Date(Date.now() - daysAgo * 86400000);
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

test.describe('AG-010 End-to-End Audit & Comparison Evidence', () => {
  test('stateful reminder ACK/SNOOZE updates overview, badge, and plan; single instance checks & ag010-* screenshots', async ({ page }) => {
    let activeReminders = [
      {
        id: 'rem-overdue-1',
        title: 'Quá hạn xịt Symbicort buổi sáng',
        message_content: 'Hãy dùng thuốc duy trì và súc miệng sạch sau khi xịt.',
        scheduled_time: '07:00',
        status: 'OVERDUE',
        is_overdue: true,
        reminder_type: 'MEDICATION',
      },
      {
        id: 'rem-pending-2',
        title: 'Đo lưu lượng đỉnh (PEF) chiều',
        message_content: 'Thổi 3 lần và nhập kết quả vào Check-in.',
        scheduled_time: '17:30',
        status: 'PENDING',
        is_overdue: false,
        reminder_type: 'CHECKIN',
      },
    ];

    const history = [
      { id: 'h1', date: getVnDateOffset(4), checkin_time: `${getVnDateOffset(4)}T07:30:00+07:00`, pef_value: 430, pef_percent: 86, spo2_value: 98, action_zone: 'GREEN', reliever_puffs: 0 },
      { id: 'h2', date: getVnDateOffset(3), checkin_time: `${getVnDateOffset(3)}T07:40:00+07:00`, pef_value: 350, pef_percent: 70, spo2_value: 96, action_zone: 'YELLOW', reliever_puffs: 1 },
      { id: 'h3', date: getVnDateOffset(2), checkin_time: `${getVnDateOffset(2)}T07:20:00+07:00`, pef_value: 445, pef_percent: 89, spo2_value: 98, action_zone: 'GREEN', reliever_puffs: 0 },
      { id: 'h4', date: getVnDateOffset(1), checkin_time: `${getVnDateOffset(1)}T07:50:00+07:00`, pef_value: 465, pef_percent: 93, spo2_value: 99, action_zone: 'GREEN', reliever_puffs: 0 },
    ];

    const carePlan = {
      patient_id: 'BN001',
      personal_best_pef: 500,
      items: [
        { id: 'cp-1', item_type: 'CONTROLLER_MED', title: 'Symbicort 160/4.5mcg', dosage: '1 nhát x 2 lần/ngày', instructions: 'Súc miệng sau khi xịt', schedule_times: ['07:00', '19:00'] },
        { id: 'cp-2', item_type: 'PEF_MEASURE', title: 'Đo lưu lượng đỉnh (PEF) buổi sáng', dosage: 'Trước khi dùng thuốc', instructions: 'Thổi 3 lần, chọn mức cao nhất', schedule_times: ['07:30'] },
      ],
    };

    await page.addInitScript(() => {
      localStorage.setItem('aftercare_token', 'mock-jwt-token');
    });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({ json: { id: 1, username: 'bn001', full_name: 'Nguyễn Văn An', role: 'patient', patient_id: 'BN001' } });
    });

    await page.route('**/api/v1/patients/*', async (route) => {
      const url = route.request().url();
      if (url.endsWith('/patients/') || url.endsWith('/patients')) {
        return route.fulfill({ json: [{ patient_id: 'BN001', full_name: 'Nguyễn Văn An', personal_best_pef: 500 }] });
      }
      return route.fulfill({
        json: {
          patient_info: { patient_id: 'BN001', full_name: 'Nguyễn Văn An', age: 58, gender: 'Nam', discharge_date: '2026-10-01' },
          clinical_status: { personal_best_pef: 500, baseline_spo2: 98, asthma_severity: 'Hen nhẹ - vừa (GINA Bậc 2)', diagnosis: 'Hen phế quản ngoại trú' },
          current_medications: { controller_med: 'Symbicort 160/4.5mcg', reliever_med: 'Ventolin HFA 100mcg' },
          follow_up: { next_appointment: '18/11/2026', doctor_in_charge: 'BS. Trần Minh Khoa', hospital: 'Bệnh viện Phổi Trung ương' },
          action_plan_rules: { green_zone: 'Duy trì thuốc hằng ngày', yellow_zone: 'Dùng thuốc cắt cơn', red_zone: 'Gọi 115 ngay' },
        },
      });
    });

    await page.route('**/api/v1/care-tracker/care-plans/**', async (route) => {
      await route.fulfill({ json: carePlan });
    });

    await page.route('**/api/v1/care-tracker/checkin/**', async (route) => {
      if (route.request().url().includes('/checkin/history/')) {
        return route.fulfill({ json: history });
      }
      return route.fulfill({ json: { id: 'ok' } });
    });

    await page.route('**/api/v1/care-tracker/reminders/active/**', async (route) => {
      await route.fulfill({ json: activeReminders });
    });

    await page.route('**/api/v1/care-tracker/reminders/*/action', async (route) => {
      const parts = route.request().url().split('/');
      const remId = parts[parts.length - 2];
      const body = route.request().postDataJSON();
      if (body?.action === 'ACKNOWLEDGE') {
        activeReminders = activeReminders.filter((r) => r.id !== remId);
      } else if (body?.action === 'SNOOZE') {
        activeReminders = activeReminders.map((r) =>
          r.id === remId ? { ...r, is_overdue: false, status: 'SNOOZED' } : r
        );
      }
      await route.fulfill({ json: { status: body?.action } });
    });

    await page.route('**/api/v1/chat/conversations*', async (route) => {
      await route.fulfill({ json: [] });
    });

    await page.route('**/api/v1/screener/evaluate', async (route) => {
      const pef = Number(route.request().postDataJSON()?.pef_value ?? 450);
      await route.fulfill({
        json: pef < 300
          ? { safety_status: 'RED_ZONE', risk_score: 5, matched_reasons: ['PEF < 60% mức tốt nhất'], action_instructions: 'Gọi 115.' }
          : { safety_status: 'GREEN_ZONE', risk_score: 0, matched_reasons: ['Chỉ số an toàn'], action_instructions: 'Tiếp tục duy trì.' },
      });
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await expect(page.locator('#patient-overview-section')).toBeVisible();

    // Verify DOM single instance invariants (1 form input, 1 checklist group)
    expect(await page.locator('#pef-number-input').count()).toBe(1);
    expect(await page.locator('.medication-reminder-container').count()).toBe(1);
    expect(await page.locator('#patient-plan-section input[type="checkbox"]').count()).toBe(2);

    // Capture AG-010 comparison desktop screenshots at 1440 & 1920
    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag010-overview-1440.png` });

    const nav = page.locator('.pw-nav-list');
    await nav.getByRole('button', { name: 'Check-in', exact: true }).click();
    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag010-checkin-1440.png` });

    await nav.getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag010-plan-1440.png` });

    await nav.getByRole('button', { name: 'Lịch sử', exact: true }).click();
    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag010-history-1440.png` });

    await page.setViewportSize({ width: 1920, height: 1080 });
    await nav.getByRole('button', { name: 'Tổng quan', exact: true }).click();
    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag010-overview-1920.png` });

    // Mobile comparison screenshots (390 & 320)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag010-mobile-390.png` });

    await page.setViewportSize({ width: 320, height: 640 });
    await page.locator('.p052-bottom-nav').getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag010-plan-320.png` });

    // Handle alert() dialogs from App.jsx ACK/SNOOZE cleanly
    page.on('dialog', (dialog) => dialog.accept());

    // Stateful SNOOZE removes overdue reminder #1 -> count drops to 1, overdue strip hides, Overview updates
    await page.setViewportSize({ width: 1440, height: 900 });
    await expect(page.locator('.pw-overdue-strip')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Thông báo nhắc nhở (2)' })).toBeVisible();

    const cards = page.locator('#patient-plan-section .reminder-alert-card');
    await cards.first().locator('.btn-snooze').click();
    await expect(page.locator('#patient-plan-section .reminder-alert-card')).toHaveCount(1);
    await expect(page.locator('.pw-overdue-strip')).toBeHidden();
    await expect(page.getByRole('button', { name: 'Thông báo nhắc nhở (1)' })).toBeVisible();

    await nav.getByRole('button', { name: 'Tổng quan', exact: true }).click();
    await expect(page.locator('#patient-overview-section')).toContainText('Đo lưu lượng đỉnh (PEF) chiều');

    // Stateful ACK on remaining reminder #2 -> count drops to 0 and empty reminder state renders cleanly
    await nav.getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    await cards.first().locator('.btn-ack').click();
    await expect(page.locator('#patient-plan-section .reminder-alert-card')).toHaveCount(0);
    await expect(page.getByText(/Không có nhắc nhở chờ/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Thông báo nhắc nhở', exact: true })).toBeVisible();
  });
});
