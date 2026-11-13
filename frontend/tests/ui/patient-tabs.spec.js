import { test, expect } from '@playwright/test';

function getVnDateOffset(daysAgo = 0) {
  const now = new Date(Date.now() - daysAgo * 86400000);
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

async function setupMockPortal(
  page,
  { history = [], carePlan = undefined, reminders = undefined, onPostCheckin = null } = {}
) {
  const resolvedCarePlan =
    carePlan === undefined
      ? {
          patient_id: 'BN001',
          personal_best_pef: 500,
          items: [
            {
              id: 'cp-1',
              item_type: 'CONTROLLER_MED',
              title: 'Symbicort 160/4.5mcg',
              dosage: '1 nhát x 2 lần/ngày',
              instructions: 'Súc miệng sạch sau khi xịt thuốc',
              schedule_times: ['07:00', '19:00'],
            },
            {
              id: 'cp-2',
              item_type: 'PEF_MEASURE',
              title: 'Đo lưu lượng đỉnh (PEF) buổi sáng',
              dosage: 'Trước khi dùng thuốc',
              instructions: 'Thổi mạnh 3 lần, chọn mức cao nhất',
              schedule_times: ['07:30'],
            },
          ],
        }
      : carePlan;

  const resolvedReminders =
    reminders === undefined
      ? [
          {
            id: 'rem-1',
            title: 'Đến giờ xịt Symbicort buổi sáng',
            message_content: 'Hãy hít 1 nhát duy trì và súc miệng sạch sau khi dùng.',
            scheduled_time: '07:00',
            status: 'PENDING',
            is_overdue: false,
            reminder_type: 'MEDICATION',
          },
        ]
      : reminders;

  await page.addInitScript(() => {
    localStorage.setItem('aftercare_token', 'mock-jwt-token');
  });

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      json: { id: 1, username: 'bn001', full_name: 'Nguyễn Văn An', role: 'patient', patient_id: 'BN001' },
    });
  });

  await page.route('**/api/v1/patients/*', async (route) => {
    const url = route.request().url();
    if (url.endsWith('/patients/') || url.endsWith('/patients')) {
      return route.fulfill({
        json: [{ patient_id: 'BN001', full_name: 'Nguyễn Văn An', personal_best_pef: 500 }],
      });
    }
    return route.fulfill({
      json: {
        patient_info: {
          patient_id: 'BN001',
          full_name: 'Nguyễn Văn An',
          age: 58,
          gender: 'Nam',
          discharge_date: '2026-10-01',
        },
        clinical_status: {
          personal_best_pef: 500,
          baseline_spo2: 98,
          asthma_severity: 'Hen nhẹ - vừa (GINA Bậc 2)',
          diagnosis: 'Hen phế quản ngoại trú',
        },
        current_medications: {
          controller_med: 'Symbicort 160/4.5mcg',
          reliever_med: 'Ventolin HFA 100mcg',
        },
        follow_up: {
          next_appointment: '18/11/2026',
          doctor_in_charge: 'BS. Trần Minh Khoa',
          hospital: 'Bệnh viện Phổi Trung ương',
        },
        action_plan_rules: {
          green_zone: 'Duy trì thuốc hằng ngày',
          yellow_zone: 'Dùng thuốc cắt cơn và theo dõi 20 phút',
          red_zone: 'Xịt cắt cơn khẩn cấp và gọi 115',
        },
      },
    });
  });

  await page.route('**/api/v1/care-tracker/care-plans/**', async (route) => {
    if (resolvedCarePlan === null) {
      return route.fulfill({ status: 404, json: { detail: 'Chưa thiết lập kế hoạch' } });
    }
    return route.fulfill({ json: resolvedCarePlan });
  });

  await page.route('**/api/v1/care-tracker/checkin/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/checkin/history/')) {
      return route.fulfill({ json: history });
    }
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      if (onPostCheckin) onPostCheckin(body);
      return route.fulfill({
        json: {
          id: 'checkin-new',
          patient_id: 'BN001',
          pef_value: body.pef_value,
          spo2_value: body.spo2_value,
          action_zone: 'GREEN',
        },
      });
    }
    return route.continue();
  });

  await page.route('**/api/v1/care-tracker/reminders/active/**', async (route) => {
    return route.fulfill({ json: resolvedReminders });
  });

  await page.route('**/api/v1/care-tracker/reminders/*/ack', async (route) => {
    return route.fulfill({ json: { status: 'ACKNOWLEDGED' } });
  });

  await page.route('**/api/v1/care-tracker/reminders/*/snooze', async (route) => {
    return route.fulfill({ json: { status: 'SNOOZED' } });
  });

  await page.route('**/api/v1/chat/conversations*', async (route) => {
    return route.fulfill({ json: [] });
  });

  await page.route('**/api/v1/screener/evaluate', async (route) => {
    return route.fulfill({
      json: {
        safety_status: 'GREEN_ZONE',
        risk_score: 0,
        matched_reasons: ['Chỉ số an toàn bình thường.'],
        action_instructions: 'Tiếp tục duy trì phác đồ.',
      },
    });
  });
}

test.describe('Patient Portal 4-Tab Architecture (AG-008)', () => {
  test('overview_has_one_summary_and_checkin_cta', async ({ page }) => {
    const yesterday = getVnDateOffset(1);
    const history = [
      {
        id: 1,
        date: yesterday,
        checkin_time: `${yesterday}T07:30:00+07:00`,
        pef_value: 460,
        pef_percent: 92,
        spo2_value: 98,
        action_zone: 'GREEN',
        reliever_puffs: 0,
      },
    ];

    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPortal(page, { history });
    await page.goto('/');

    const overview = page.locator('#patient-overview-section');
    await expect(overview).toBeVisible();

    // Hidden tabs must not be visible on default overview tab
    await expect(page.locator('#patient-checkin-section')).toBeHidden();
    await expect(page.locator('#patient-plan-section')).toBeHidden();
    await expect(page.locator('#patient-history-section')).toBeHidden();

    // Overview must NOT render full chart, full checklist, form, preview, or duplicate status/CTA cards
    await expect(overview.locator('.pw-chart-bars')).toHaveCount(0);
    await expect(overview.locator('#pef-number-input')).toHaveCount(0);
    await expect(overview.locator('input[type="checkbox"]')).toHaveCount(0);
    await expect(overview.getByText('Xem trước biểu mẫu:')).toHaveCount(0);
    await expect(overview.getByRole('heading', { name: 'Kiểm tra triệu chứng' })).toHaveCount(0);
    await expect(overview.getByRole('heading', { name: 'Nhật ký gần nhất' })).toHaveCount(0);

    // Exactly ONE primary check-in CTA in Overview
    const primaryCtas = overview.locator('.pw-btn-primary');
    await expect(primaryCtas).toHaveCount(1);
    await expect(primaryCtas).toContainText('Check-in hôm nay');

    // Consistent saved metrics (PEF + SpO2 + timestamp from yesterday) and follow-up date
    await expect(overview).toContainText('460');
    await expect(overview).toContainText('98%');
    await expect(overview).toContainText('18/11/2026');
  });

  test('tabs_route_actions_to_owned_content', async ({ page }) => {
    const today = getVnDateOffset(0);
    const history = [
      {
        id: 1,
        date: today,
        checkin_time: `${today}T07:15:00+07:00`,
        pef_value: 485,
        pef_percent: 97,
        spo2_value: 99,
        action_zone: 'GREEN',
        reliever_puffs: 0,
      },
    ];

    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPortal(page, { history });
    await page.goto('/');

    const sidebar = page.locator('.pw-sidebar');
    await expect(sidebar.getByRole('button', { name: 'Tổng quan', exact: true })).toHaveAttribute('aria-current', 'page');
    await expect(sidebar.getByRole('button', { name: 'Check-in', exact: true })).toBeVisible();
    await expect(sidebar.getByRole('button', { name: 'Kế hoạch', exact: true })).toBeVisible();
    await expect(sidebar.getByRole('button', { name: 'Lịch sử', exact: true })).toBeVisible();

    // Time filter must NOT live in Topbar on non-history tabs
    await expect(page.locator('.pw-topbar .pw-period-pills')).toHaveCount(0);

    // Overview CTA routes to Check-in tab and focuses PEF input
    await page.locator('#patient-overview-section .pw-btn-primary').click();
    await expect(page.locator('#patient-checkin-section')).toBeVisible();
    await expect(page.locator('#patient-overview-section')).toBeHidden();
    await expect(page.locator('#pef-number-input')).toBeFocused();
    await expect(page.locator('.pw-period-pills')).toBeHidden();

    // Plan tab owns checklist, reminders, and profile/care plan
    await sidebar.getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    await expect(page.locator('#patient-plan-section')).toBeVisible();
    await expect(page.locator('#patient-plan-section').getByText('Symbicort 160/4.5mcg').first()).toBeVisible();
    await expect(page.locator('#patient-plan-section .reminder-alert-card')).toHaveCount(1);
    await expect(page.locator('#patient-plan-section').getByText('Hồ Sơ Xuất Viện & Kế Hoạch Cá Nhân')).toBeVisible();

    // History tab owns time filter, PEF chart, 14-day grid, and detailed log
    await sidebar.getByRole('button', { name: 'Lịch sử', exact: true }).click();
    await expect(page.locator('#patient-history-section')).toBeVisible();
    await expect(page.locator('#patient-history-section .pw-period-pills')).toBeVisible();
    await expect(page.locator('#patient-history-section .pw-chart-bars')).toBeVisible();
    await expect(page.locator('#patient-history-section').getByText('Lưới Theo Dõi 14 Ngày')).toBeVisible();

    // HOPI chat remains accessible from sidebar
    await sidebar.getByRole('button', { name: 'Hỏi trợ lý HOPI' }).click();
    await expect(page.locator('.chat-popup')).toBeVisible();
  });

  test('preserves form input, 20m yellow countdown timer, and avoids unintended POST across all 4 tabs and resize', async ({ page }) => {
    let postCount = 0;
    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPortal(page, {
      history: [],
      reminders: [],
      onPostCheckin: () => {
        postCount += 1;
      },
    });
    await page.goto('/');

    // Enter Check-in tab and set YELLOW zone PEF (350/500 = 70%)
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();
    const pefInput = page.locator('#pef-number-input');
    await pefInput.fill('350');
    await expect(page.getByText(/Bộ đếm giờ an toàn 20 phút:/)).toBeVisible();

    // Wait 1.2s so timer ticks down from 20:00
    await page.waitForTimeout(1200);
    const timerBefore = await page.getByText(/Bộ đếm giờ an toàn 20 phút:/).textContent();
    expect(timerBefore).not.toContain('20:00');

    // Visit Plan, History, Overview, resize to mobile 390x844, then return to Check-in via mobile bottom nav
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Lịch sử', exact: true }).click();
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Tổng quan', exact: true }).click();

    await page.setViewportSize({ width: 390, height: 844 });
    const bottomNav = page.locator('.p052-bottom-nav');
    await expect(bottomNav.locator('button')).toHaveCount(4);
    await bottomNav.getByRole('button', { name: 'Check-in', exact: true }).click();

    await expect(pefInput).toHaveValue('350');
    const timerAfter = await page.getByText(/Bộ đếm giờ an toàn 20 phút:/).textContent();
    expect(timerAfter).not.toContain('20:00');
    expect(postCount).toBe(0);

    // Only explicit submit triggers POST once
    await page.getByRole('button', { name: 'Lưu đánh giá hôm nay' }).click();
    await expect.poll(() => postCount).toBe(1);
  });

  test('overdue reminder is recognizable across all 4 tabs without acting as emergency medical alert', async ({ page }) => {
    const overdueReminders = [
      {
        id: 'rem-overdue',
        title: 'Đã quá giờ xịt Symbicort sáng',
        message_content: 'Hãy hít 1 nhát duy trì ngay.',
        scheduled_time: '07:00',
        status: 'OVERDUE',
        is_overdue: true,
        reminder_type: 'MEDICATION',
      },
    ];

    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPortal(page, { history: [], reminders: overdueReminders });
    await page.goto('/');

    // Overdue notice visible across tabs, and must NOT show tel:115 emergency medical banner
    for (const tabLabel of ['Tổng quan', 'Check-in', 'Lịch sử', 'Kế hoạch']) {
      await page.locator('.pw-sidebar').getByRole('button', { name: tabLabel, exact: true }).click();
      await expect(page.locator('.pw-priority-zone.red')).toHaveCount(0);
      await expect(page.locator('.pw-overdue-strip')).toBeVisible();
      await expect(page.locator('.pw-overdue-strip')).toContainText('Đã quá giờ xịt Symbicort sáng');
    }

    // Full reminder card with ACK/SNOOZE is in Plan tab
    await expect(page.locator('#patient-plan-section .reminder-alert-card.overdue')).toHaveCount(1);
    await expect(page.locator('#patient-plan-section .btn-ack')).toBeVisible();
    await expect(page.locator('#patient-plan-section .btn-snooze')).toBeVisible();
  });
});
