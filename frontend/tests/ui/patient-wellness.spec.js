import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const SCREENSHOT_DIR = path.resolve(process.cwd(), '../docs/design-handoff/screenshots');

function getVnDateOffset(daysAgo = 0) {
  const now = new Date(Date.now() - daysAgo * 86400000);
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

async function setupMockPatientPortal(page, { history = [], carePlan = undefined, reminders = undefined } = {}) {
  const today = getVnDateOffset(0);
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
            is_overdue: false,
            action_type: 'CONTROLLER_MED',
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
          phone: '0901234567',
          address: 'Quận 1, TP.HCM',
        },
        clinical_status: {
          personal_best_pef: 500,
          baseline_spo2: 98,
          asthma_severity: 'Hen nhẹ - vừa (GINA Bậc 2)',
        },
        current_medications: {
          controller_med: 'Symbicort 160/4.5mcg',
          reliever_med: 'Ventolin HFA 100mcg',
        },
        follow_up: {
          next_appointment: '18/11/2026',
          doctor_in_charge: 'BS. Trần Minh Khoa',
        },
        action_plan_rules: {
          green_zone_min_pef: 400,
          yellow_zone_min_pef: 300,
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

  await page.route('**/api/v1/care-tracker/checkin/history/**', async (route) => {
    return route.fulfill({ json: history });
  });

  await page.route('**/api/v1/care-tracker/reminders/active/**', async (route) => {
    return route.fulfill({ json: resolvedReminders });
  });

  await page.route('**/api/v1/chat/conversations*', async (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({ json: { id: 101, title: 'Tư vấn khẩn' } });
    }
    return route.fulfill({ json: [] });
  });

  await page.route('**/api/v1/chat/conversations/**', async (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({
        json: { id: 901, role: 'assistant', content: 'Hãy ngồi thẳng và xịt thuốc cắt cơn theo phác đồ.' },
      });
    }
    return route.fulfill({ json: { id: 101, title: 'Tư vấn khẩn', messages: [] } });
  });

  await page.route('**/api/v1/screener/evaluate', async (route) => {
    return route.fulfill({
      json: {
        safety_status: 'GREEN_ZONE',
        risk_score: 0,
        summary_vi: 'Kiểm soát hen tốt.',
        actions_vi: ['Tiếp tục thuốc duy trì hằng ngày.'],
      },
    });
  });

  return { today };
}

test.describe('Patient Wellness Dashboard (AG-008 4-Tab Flow)', () => {
  test('Desktop 1440px renders flat clinical Wellness shell across all 4 owned tabs and real PEF trend', async ({ page }) => {
    const history = [
      { id: 1, date: getVnDateOffset(4), checkin_time: `${getVnDateOffset(4)}T07:30:00+07:00`, pef_value: 440, pef_percent: 88, spo2_value: 98, action_zone: 'GREEN', reliever_puffs: 0 },
      { id: 2, date: getVnDateOffset(3), checkin_time: `${getVnDateOffset(3)}T07:45:00+07:00`, pef_value: 390, pef_percent: 78, spo2_value: 96, action_zone: 'YELLOW', reliever_puffs: 2 },
      { id: 3, date: getVnDateOffset(2), checkin_time: `${getVnDateOffset(2)}T08:10:00+07:00`, pef_value: 460, pef_percent: 92, spo2_value: 98, action_zone: 'GREEN', reliever_puffs: 0 },
      { id: 4, date: getVnDateOffset(1), checkin_time: `${getVnDateOffset(1)}T07:20:00+07:00`, pef_value: 475, pef_percent: 95, spo2_value: 99, action_zone: 'GREEN', reliever_puffs: 0 },
      { id: 5, date: getVnDateOffset(0), checkin_time: `${getVnDateOffset(0)}T07:15:00+07:00`, pef_value: 485, pef_percent: 97, spo2_value: 99, action_zone: 'GREEN', reliever_puffs: 0 },
    ];

    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPatientPortal(page, { history });
    await page.goto('/');

    // Single header/shell: old .p052-header and .chat-fab must NOT appear on patient portal
    await expect(page.locator('.p052-header')).toHaveCount(0);
    await expect(page.locator('.chat-fab')).toHaveCount(0);
    await expect(page.locator('.pw-sidebar')).toBeVisible();
    await expect(page.locator('.pw-topbar')).toBeVisible();

    // Overview tab: compact welcome, single primary CTA, latest saved PEF + SpO2, next task
    const overview = page.locator('#patient-overview-section');
    await expect(overview).toBeVisible();
    await expect(overview.getByRole('heading', { name: 'Chào Nguyễn Văn An' })).toBeVisible();
    await expect(overview.getByText('Đã check-in hôm nay')).toBeVisible();
    await expect(overview.locator('.pw-welcome-actions .pw-btn-primary')).toHaveCount(1);
    await expect(overview.locator('.pw-welcome-actions .pw-btn-primary')).toContainText('Cập nhật check-in hôm nay');
    await expect(overview.locator('.pw-welcome-actions .pw-btn-outline-blue')).toContainText('Trò chuyện với HOPI');
    await expect(overview.locator('.pw-welcome-actions .pw-link-btn')).toContainText('Kế hoạch & Hồ sơ');
    await expect(overview.getByRole('heading', { name: 'Chỉ số đã lưu gần nhất' })).toBeVisible();
    await expect(overview.locator('.pw-big-metric')).toContainText('485 L/phút');
    await expect(overview.locator('.pw-mini-value')).toContainText('99%');

    // No horizontal overflow
    const hasOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(hasOverflow).toBe(false);

    // AG-006 flat palette checks preserved on AG-008 shell
    const agStyles = await page.evaluate(() => {
      const portal = getComputedStyle(document.querySelector('.portal-patient'));
      const shell = getComputedStyle(document.querySelector('.pw-shell'));
      const card = getComputedStyle(document.querySelector('.pw-card'));
      const welcome = getComputedStyle(document.querySelector('.pw-welcome-card'));
      const pefCard = getComputedStyle(document.querySelector('.pw-blue-metric-card'));
      const primaryBtn = getComputedStyle(document.querySelector('.pw-welcome-actions .pw-btn-primary'));
      return {
        portalBg: portal.backgroundColor,
        portalBgImg: portal.backgroundImage,
        shellShadow: shell.boxShadow,
        shellRadius: shell.borderTopLeftRadius,
        cardBg: card.backgroundColor,
        cardShadow: card.boxShadow,
        cardRadius: card.borderTopLeftRadius,
        welcomeBg: welcome.backgroundColor,
        welcomeBgImg: welcome.backgroundImage,
        pefCardBg: pefCard.backgroundColor,
        pefCardShadow: pefCard.boxShadow,
        primaryBtnBg: primaryBtn.backgroundColor,
        primaryBtnRadius: primaryBtn.borderTopLeftRadius,
        primaryBtnShadow: primaryBtn.boxShadow,
      };
    });
    expect(agStyles.portalBg).toBe('rgb(245, 247, 250)');
    expect(agStyles.portalBgImg).toBe('none');
    expect(agStyles.shellShadow).toBe('none');
    expect(agStyles.shellRadius).toBe('16px');
    expect(agStyles.cardBg).toBe('rgb(255, 255, 255)');
    expect(agStyles.cardShadow).toBe('none');
    expect(agStyles.cardRadius).toBe('14px');
    expect(agStyles.welcomeBg).toBe('rgb(239, 246, 255)');
    expect(agStyles.welcomeBgImg).toBe('none');
    expect(agStyles.pefCardBg).toBe('rgb(255, 255, 255)');
    expect(agStyles.pefCardShadow).toBe('none');
    expect(agStyles.primaryBtnBg).toBe('rgb(37, 104, 212)');
    expect(agStyles.primaryBtnRadius).toBe('8px');
    expect(agStyles.primaryBtnShadow).toBe('none');

    // Screenshot 1: Overview
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForFunction(() => window.scrollY === 0);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ag008-overview-1440.png'), fullPage: false });

    // Tab 2: Check-in
    const sidebar = page.locator('.pw-sidebar');
    await sidebar.getByRole('button', { name: 'Check-in', exact: true }).click();
    await expect(page.locator('#patient-checkin-section')).toBeVisible();
    const saveBg = await page.getByRole('button', { name: 'Lưu đánh giá hôm nay' }).evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(saveBg).toBe('rgb(37, 104, 212)');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ag008-checkin-1440.png'), fullPage: false });

    // Tab 3: Plan (checklist + reminders + profile)
    await sidebar.getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    await expect(page.locator('#patient-plan-section')).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ag008-plan-1440.png'), fullPage: false });

    // Keyboard accessibility check: native checkbox focus & Space toggle on CarePlan inside Plan tab
    const firstCheckbox = page.locator('#careplan-item-cp-1');
    await firstCheckbox.focus();
    await expect(firstCheckbox).toBeFocused();
    await page.keyboard.press('Space');
    await expect(firstCheckbox).toBeChecked();

    const measureCheckbox = page.locator('#careplan-measure-cp-2');
    await measureCheckbox.focus();
    await expect(measureCheckbox).toBeFocused();
    await page.keyboard.press('Space');
    await expect(measureCheckbox).toBeChecked();

    // Tab 4: History (time filter + PEF bar chart + 14-day grid + log)
    await sidebar.getByRole('button', { name: 'Lịch sử', exact: true }).click();
    const historySec = page.locator('#patient-history-section');
    await expect(historySec).toBeVisible();
    await expect(historySec.getByRole('heading', { name: 'Xu hướng PEF' })).toBeVisible();
    await expect(historySec.getByText('14 ngày gần nhất • 5 lần đo thật')).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ag008-history-1440.png'), fullPage: false });

    // Click an earlier bar in the real PEF trend chart and verify inspector updates
    const yellowBar = historySec.locator('.pw-bar-col').nth(1);
    await yellowBar.click();
    await expect(historySec.locator('.pw-chart-inspector')).toContainText('PEF 390 L/phút (78%)');
    await expect(historySec.locator('.pw-chart-inspector')).toContainText('Cảnh báo');
  });

  test('Empty history and empty care plan show honest empty states without faking metrics or next tasks', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPatientPortal(page, { history: [], carePlan: null, reminders: [] });
    await page.goto('/');

    const overview = page.locator('#patient-overview-section');
    await expect(overview.getByText('Chưa check-in hôm nay')).toBeVisible();
    await expect(overview.getByText('Chưa có kết quả PEF đã lưu')).toBeVisible();
    await expect(overview.locator('.pw-blue-metric-card')).toContainText('-- L/phút');
    await expect(overview).toContainText('Chưa có phác đồ chăm sóc hoặc nhắc nhở đang kích hoạt');

    // Check-in tab clarifies no saved log today even though form defaults exist
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();
    await expect(page.getByText('Hôm nay chưa có bản ghi đã lưu')).toBeVisible();

    // History tab shows disabled current-month pill when empty
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Lịch sử', exact: true }).click();
    await expect(page.getByRole('button', { name: /\(Chưa có dữ liệu\)/ })).toBeDisabled();
  });

  test('Long CarePlan (5 items) keeps Overview concise and renders full checklist in Plan tab', async ({ page }) => {
    const history = [
      { id: 1, date: getVnDateOffset(1), checkin_time: `${getVnDateOffset(1)}T07:30:00+07:00`, pef_value: 470, pef_percent: 94, spo2_value: 99, action_zone: 'GREEN', reliever_puffs: 0 },
    ];
    const longCarePlan = {
      patient_id: 'BN001',
      personal_best_pef: 500,
      items: [
        { id: 'cp-1', item_type: 'CONTROLLER_MED', title: 'Symbicort 160/4.5mcg (Sáng)', dosage: '1 nhát hít', instructions: 'Súc miệng sạch sau khi dùng', schedule_times: ['07:00'] },
        { id: 'cp-2', item_type: 'CONTROLLER_MED', title: 'Symbicort 160/4.5mcg (Tối)', dosage: '1 nhát hít', instructions: 'Súc miệng sạch sau khi dùng', schedule_times: ['19:00'] },
        { id: 'cp-3', item_type: 'CONTROLLER_MED', title: 'Montelukast 10mg', dosage: '1 viên/tối', instructions: 'Uống trước khi ngủ', schedule_times: ['21:00'] },
        { id: 'cp-4', item_type: 'PEF_MEASURE', title: 'Đo lưu lượng đỉnh (PEF) sáng', dosage: 'Trước thuốc', instructions: 'Thổi mạnh 3 lần, lấy số cao nhất' },
        { id: 'cp-5', item_type: 'PEF_MEASURE', title: 'Đo lưu lượng đỉnh (PEF) tối & SpO2', dosage: 'Trước khi ngủ', instructions: 'Ghi nhận lại nếu thấy tức ngực' },
      ],
    };

    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPatientPortal(page, { history, carePlan: longCarePlan });
    await page.goto('/');

    // Overview stays short (no full 5-item checklist)
    await expect(page.locator('#patient-overview-section input[type="checkbox"]')).toHaveCount(0);

    // Plan tab displays all 5 items
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    await expect(page.getByText('Symbicort 160/4.5mcg (Sáng)')).toBeVisible();
    await expect(page.getByText('Đo lưu lượng đỉnh (PEF) tối & SpO2')).toBeVisible();
  });

  test('Yesterday saved log distinguishes saved date from not checked in today', async ({ page }) => {
    const yesterday = getVnDateOffset(1);
    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPatientPortal(page, {
      history: [
        {
          id: 9,
          date: yesterday,
          checkin_time: `${yesterday}T08:00:00+07:00`,
          pef_value: 430,
          pef_percent: 86,
          spo2_value: 97,
          action_zone: 'GREEN',
          reliever_puffs: 0,
        },
      ],
    });
    await page.goto('/');

    await expect(page.getByText('Chưa check-in hôm nay')).toBeVisible();
    await expect(page.locator('.pw-blue-metric-card')).toContainText('430 L/phút');
    await expect(page.locator('.pw-blue-metric-card')).toContainText('97%');
    await expect(page.locator('.pw-blue-pill')).toContainText('08:00');

    await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();
    await expect(page.getByText('Hôm nay chưa có bản ghi đã lưu')).toBeVisible();
  });

  test('Historical RED check-in with GREEN live form does NOT trigger active top emergency alert', async ({ page }) => {
    const oldRedDate = getVnDateOffset(3);
    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPatientPortal(page, {
      history: [
        {
          id: 19,
          date: oldRedDate,
          checkin_time: `${oldRedDate}T09:15:00+07:00`,
          pef_value: 250,
          pef_percent: 50,
          spo2_value: 92,
          action_zone: 'RED',
          reliever_puffs: 4,
        },
      ],
      reminders: [],
    });
    await page.goto('/');

    // Historical RED record while live check-in state is GREEN must NOT become an active emergency banner
    await expect(page.locator('.pw-priority-zone')).toHaveCount(0);
    await expect(page.getByText('Chưa check-in hôm nay')).toBeVisible();
    await expect(
      page.locator('.pw-welcome-meta .pw-status-chip', { hasText: 'Lần cuối' }),
    ).toContainText(/Lần cuối \(\d{2}-\d{2}\): Vùng Đỏ/);
    await expect(page.locator('.pw-blue-metric-card')).toContainText('250 L/phút');

    // Other tabs also must NOT show active emergency alert when live form is GREEN
    for (const tabName of ['Check-in', 'Kế hoạch', 'Lịch sử']) {
      await page.locator('.pw-sidebar').getByRole('button', { name: tabName, exact: true }).click();
      await expect(page.locator('.pw-priority-zone')).toHaveCount(0);
    }
  });

  test('Active RED zone alert uses canonical copy and persists across all 4 tabs with 115 & HOPI', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPatientPortal(page, { history: [], reminders: [] });
    await page.goto('/');

    // Enter Check-in and fill PEF = 250 (< 60% of 500 -> live RED zone)
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();
    const pefInput = page.locator('#pef-number-input');
    await pefInput.fill('250');

    const redAlert = page.locator('.pw-priority-zone.red');
    for (const tabName of ['Check-in', 'Tổng quan', 'Kế hoạch', 'Lịch sử']) {
      await page.locator('.pw-sidebar').getByRole('button', { name: tabName, exact: true }).click();
      await expect(redAlert).toBeVisible();
      await expect(redAlert).toContainText('Cảnh Báo Cờ Đỏ Cấp Cứu');
      await expect(redAlert).toContainText('Cần Hỗ Trợ Y Tế Khẩn Cấp! PEF dưới 60%');
      await expect(redAlert.locator('a[href="tel:115"]')).toContainText('Gọi cấp cứu 115 ngay');
    }

    // Open HOPI chat via shell alert action
    await redAlert.getByRole('button', { name: 'Hỏi Trợ lý Hopi hướng dẫn' }).click();
    await expect(page.locator('.chat-popup')).toBeVisible();
  });

  test('Mobile 390x844 has compact header, 4-tab bottom nav, welcome + single primary CTA at scrollY=0, and zero overflow', async ({ page }) => {
    const history = [
      { id: 1, date: getVnDateOffset(2), checkin_time: `${getVnDateOffset(2)}T07:30:00+07:00`, pef_value: 450, pef_percent: 90, spo2_value: 98, action_zone: 'GREEN', reliever_puffs: 0 },
      { id: 2, date: getVnDateOffset(0), checkin_time: `${getVnDateOffset(0)}T07:10:00+07:00`, pef_value: 470, pef_percent: 94, spo2_value: 99, action_zone: 'GREEN', reliever_puffs: 0 },
    ];
    const overdueReminders = [
      {
        id: 'rem-overdue',
        title: 'Đã quá giờ xịt Symbicort sáng',
        message_content: 'Hãy hít 1 nhát duy trì ngay và súc miệng sạch sau khi dùng.',
        scheduled_time: '07:00',
        status: 'OVERDUE',
        reminder_type: 'MEDICATION',
      },
    ];

    await page.setViewportSize({ width: 390, height: 844 });
    await setupMockPatientPortal(page, { history, reminders: overdueReminders });
    await page.goto('/');

    await expect(page.locator('.p052-bottom-nav')).toBeVisible();
    await expect(page.locator('.p052-bottom-nav button')).toHaveCount(4);
    await expect(page.locator('.pw-mobile-bar')).toBeVisible();
    await expect(page.locator('.chat-fab')).toHaveCount(0);
    await expect(page.locator('#patient-overview-section .pw-btn-primary')).toHaveCount(1);

    const hasOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(hasOverflow).toBe(false);

    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForFunction(() => window.scrollY === 0);

    const layout = await page.evaluate(() => {
      const topbar = document.querySelector('.pw-topbar')?.getBoundingClientRect();
      const overdueStrip = document.querySelector('.pw-overdue-strip')?.getBoundingClientRect();
      const welcomeCard = document.querySelector('.pw-welcome-card')?.getBoundingClientRect();
      const welcomeActions = document.querySelector('.pw-welcome-actions')?.getBoundingClientRect();
      const btnMetrics = Array.from(document.querySelectorAll('.pw-welcome-actions button')).map((b) => {
        const r = b.getBoundingClientRect();
        return { centerY: Math.round((r.top + r.bottom) / 2) };
      });
      const rows = [];
      for (const m of btnMetrics) {
        if (!rows.some((y) => Math.abs(y - m.centerY) <= 12)) rows.push(m.centerY);
      }
      const bottomNav = document.querySelector('.p052-bottom-nav')?.getBoundingClientRect();
      return {
        scrollY: window.scrollY,
        topbarTop: topbar ? topbar.top : -1,
        headerBottom: topbar ? topbar.bottom : 9999,
        overdueTop: overdueStrip ? overdueStrip.top : 9999,
        welcomeTop: welcomeCard ? welcomeCard.top : 9999,
        welcomeActionsBottom: welcomeActions ? welcomeActions.bottom : 9999,
        welcomeActionRows: rows.length,
        bottomNavTop: bottomNav ? bottomNav.top : 844,
      };
    });

    expect(layout.scrollY).toBe(0);
    expect(layout.topbarTop).toBeGreaterThanOrEqual(0);
    expect(layout.headerBottom).toBeLessThanOrEqual(120);
    expect(layout.overdueTop).toBeLessThan(layout.welcomeTop);
    expect(layout.welcomeActionsBottom).toBeLessThanOrEqual(layout.bottomNavTop);
    expect(layout.welcomeActionRows).toBeLessThanOrEqual(2);

    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'ag008-mobile-390.png'), fullPage: false });
  });

  test('Narrow 320px and root-font-size probe (32px) wrap cleanly without horizontal overflow', async ({ page }) => {
    const history = [
      { id: 1, date: getVnDateOffset(0), checkin_time: `${getVnDateOffset(0)}T07:10:00+07:00`, pef_value: 470, pef_percent: 94, spo2_value: 99, action_zone: 'GREEN', reliever_puffs: 0 },
    ];
    await page.setViewportSize({ width: 320, height: 640 });
    await setupMockPatientPortal(page, { history });
    await page.goto('/');

    const narrowOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(narrowOverflow).toBe(false);

    // Explicit root-font-size probe (scales Tailwind rem tokens; fixed-px .pw-* classes stay fixed)
    await page.evaluate(() => {
      document.documentElement.style.fontSize = '32px';
    });
    const probeOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(probeOverflow).toBe(false);
  });

  test('Responsive reflow at CSS area equivalent to 200% zoom from 1440x900 (720x450, DPR 2; not real browser zoom)', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 720, height: 450 }, deviceScaleFactor: 2 });
    const page = await context.newPage();
    try {
      const history = [
        { id: 1, date: getVnDateOffset(0), checkin_time: `${getVnDateOffset(0)}T07:10:00+07:00`, pef_value: 470, pef_percent: 94, spo2_value: 99, action_zone: 'GREEN', reliever_puffs: 0 },
      ];
      await setupMockPatientPortal(page, { history });
      await page.goto('/');

      await expect(page.locator('.pw-topbar')).toBeVisible();
      await expect(page.locator('#patient-overview-section .pw-btn-primary')).toHaveCount(1);
      await expect(page.locator('#patient-overview-section .pw-btn-primary')).toBeVisible();

      const hasOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
      expect(hasOverflow).toBe(false);
    } finally {
      await context.close();
    }
  });

  test('Nurse portal keeps Header & chat-fab untouched and switches to Wellness preview cleanly', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await setupMockPatientPortal(page, { history: [] });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        json: { id: 2, username: 'nurse1', full_name: 'ĐD Trần Lan', role: 'nurse', patient_id: null },
      });
    });

    await page.route('**/api/v1/care-tracker/nurse/overview', async (route) => {
      await route.fulfill({
        json: [{ patient_id: 'BN001', full_name: 'Nguyễn Văn An', action_zone: 'GREEN', today_checked_in: false }],
      });
    });

    await page.route('**/api/v1/escalations/**', async (route) => {
      await route.fulfill({ json: [] });
    });

    await page.goto('/');

    await expect(page.locator('.p052-header')).toBeVisible();
    await expect(page.locator('.chat-fab')).toBeVisible();
    await expect(page.locator('.pw-shell')).toHaveCount(0);

    await page.getByRole('button', { name: 'Bệnh nhân', exact: true }).click();
    await expect(page.locator('.pw-shell')).toBeVisible();
    await expect(page.locator('.p052-header')).toHaveCount(0);
    await expect(page.locator('.chat-fab')).toHaveCount(0);
    await expect(page.getByLabel('Chọn bệnh nhân')).toBeVisible();
  });
});
