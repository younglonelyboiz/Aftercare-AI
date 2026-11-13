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

async function setupResponsivePortal(
  page,
  {
    patientName = 'Nguyễn Thị Minh Phương Thanh Thảo',
    history = [],
    carePlanItems = undefined,
    reminders = undefined,
    onAck = null,
    onSnooze = null,
  } = {}
) {
  const resolvedItems = carePlanItems ?? [
    {
      id: 'cp-1',
      item_type: 'CONTROLLER_MED',
      title: 'Budesonide/Formoterol Turbuhaler 160/4.5mcg hít duy trì',
      dosage: '1-2 nhát x 2 lần/ngày (sáng trước ăn và tối trước ngủ)',
      instructions: 'Hít sâu dứt khoát bằng miệng, giữ hơi thở 10 giây rồi súc miệng bằng nước sạch và nhổ bỏ.',
      schedule_times: ['07:00', '19:00'],
    },
    {
      id: 'cp-2',
      item_type: 'CONTROLLER_MED',
      title: 'Montelukast Sodium 10mg uống buổi tối',
      dosage: '1 viên/lần trước khi đi ngủ 30 phút',
      instructions: 'Uống nguyên viên với nước lọc, không tự ý ngưng thuốc ngay cả khi không còn khò khè.',
      schedule_times: ['21:00'],
    },
    {
      id: 'cp-3',
      item_type: 'PEF_MEASURE',
      title: 'Đo lưu lượng đỉnh (PEF) và SpO₂ trước liều thuốc sáng',
      dosage: '3 lần thổi lấy trị số cao nhất',
      instructions: 'Đứng thẳng, ngậm kín ống thổi và thổi ra thật nhanh mạnh trong một nhịp.',
      schedule_times: ['07:00'],
    },
    {
      id: 'cp-4',
      item_type: 'COMORBIDITY_MED',
      title: 'Omeprazole 20mg hỗ trợ kiểm soát trào ngược dạ dày thực quản',
      dosage: '1 viên trước ăn sáng 30 phút',
      instructions: 'Tránh nằm ngay sau bữa tối ít nhất 2 giờ để hạn chế khởi phát cơn hen về đêm.',
      schedule_times: ['06:30'],
    },
    {
      id: 'cp-5',
      item_type: 'CONTROLLER_MED',
      title: 'Nước muối sinh lý Natri Clorid 0.9% rửa mũi họng buổi tối',
      dosage: '2 lần/ngày khi thời tiết chuyển mùa',
      instructions: 'Giữ thông thoáng đường thở trên, hạn chế dị nguyên bụi mịn kích thích phế quản.',
      schedule_times: ['20:30'],
    },
  ];

  const resolvedReminders = reminders ?? [
    {
      id: 'rem-overdue-1',
      title: 'Quá hạn xịt Symbicort Turbuhaler liều buổi sáng',
      message_content: 'Hãy hít đủ liều duy trì và súc miệng sạch ngay sau khi dùng để phòng nấm họng.',
      scheduled_time: '07:00',
      status: 'OVERDUE',
      is_overdue: true,
      reminder_type: 'MEDICATION',
    },
    {
      id: 'rem-pending-2',
      title: 'Sắp đến giờ đo lưu lượng đỉnh (PEF) buổi chiều',
      message_content: 'Chuẩn bị lưu lượng đỉnh kế sạch, thổi 3 lần và nhập kết quả vào mục Check-in.',
      scheduled_time: '17:30',
      status: 'PENDING',
      is_overdue: false,
      reminder_type: 'CHECKIN',
    },
  ];

  await page.addInitScript(() => {
    localStorage.setItem('aftercare_token', 'mock-jwt-token');
  });

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      json: { id: 1, username: 'bn001', full_name: patientName, role: 'patient', patient_id: 'BN001' },
    });
  });

  await page.route('**/api/v1/patients/*', async (route) => {
    const url = route.request().url();
    if (url.endsWith('/patients/') || url.endsWith('/patients')) {
      return route.fulfill({
        json: [{ patient_id: 'BN001', full_name: patientName, personal_best_pef: 500 }],
      });
    }
    return route.fulfill({
      json: {
        patient_info: {
          patient_id: 'BN001',
          full_name: patientName,
          age: 58,
          gender: 'Nữ',
          discharge_date: '2026-10-01',
        },
        clinical_status: {
          personal_best_pef: 500,
          baseline_spo2: 98,
          asthma_severity: 'Hen nhẹ - vừa (GINA Bậc 2)',
          diagnosis: 'Hen phế quản ngoại trú kèm viêm mũi dị ứng',
        },
        current_medications: {
          controller_med: 'Symbicort Turbuhaler 160/4.5mcg',
          reliever_med: 'Ventolin HFA 100mcg',
        },
        follow_up: {
          next_appointment: '18/11/2026',
          doctor_in_charge: 'PGS.TS.BS. Trần Minh Khoa Nguyên',
          hospital: 'Bệnh viện Phổi Trung ương',
        },
        action_plan_rules: {
          green_zone: 'Duy trì thuốc hằng ngày đúng giờ',
          yellow_zone: 'Dùng thuốc cắt cơn và theo dõi 20 phút',
          red_zone: 'Xịt cắt cơn khẩn cấp và gọi 115 ngay',
        },
      },
    });
  });

  await page.route('**/api/v1/care-tracker/care-plans/**', async (route) => {
    return route.fulfill({
      json: {
        patient_id: 'BN001',
        personal_best_pef: 500,
        items: resolvedItems,
      },
    });
  });

  await page.route('**/api/v1/care-tracker/checkin/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/checkin/history/')) {
      return route.fulfill({ json: history });
    }
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      return route.fulfill({
        json: {
          id: 'checkin-new',
          patient_id: 'BN001',
          pef_value: body.pef_value,
          spo2_value: body.spo2_value,
          action_zone: 'YELLOW',
        },
      });
    }
    return route.continue();
  });

  await page.route('**/api/v1/care-tracker/reminders/active/**', async (route) => {
    return route.fulfill({ json: resolvedReminders });
  });

  await page.route('**/api/v1/care-tracker/reminders/*/action', async (route) => {
    const body = route.request().postDataJSON();
    if (body?.action === 'ACKNOWLEDGE' && onAck) onAck(route.request().url());
    if (body?.action === 'SNOOZE' && onSnooze) onSnooze(route.request().url());
    return route.fulfill({ json: { status: body?.action || 'OK' } });
  });

  await page.route('**/api/v1/chat/conversations*', async (route) => {
    return route.fulfill({ json: [] });
  });

  await page.route('**/api/v1/screener/evaluate', async (route) => {
    const body = route.request().postDataJSON();
    const pef = Number(body?.pef_value ?? 450);
    const isYellow = pef > 0 && pef < 400;
    return route.fulfill({
      json: isYellow
        ? {
            safety_status: 'YELLOW_ZONE',
            risk_score: 2,
            matched_reasons: ['PEF giảm còn 67% mức tốt nhất (335/500 L/phút).'],
            action_instructions: 'Dùng thuốc cắt cơn và theo dõi 20 phút.',
          }
        : {
            safety_status: 'GREEN_ZONE',
            risk_score: 0,
            matched_reasons: ['Chỉ số an toàn bình thường.'],
            action_instructions: 'Tiếp tục duy trì phác đồ.',
          },
    });
  });
}

function buildWeekHistory() {
  return [
    {
      id: 'c4',
      date: getVnDateOffset(5),
      checkin_time: `${getVnDateOffset(5)}T07:20:00+07:00`,
      pef_value: 470,
      pef_percent: 94,
      spo2_value: 99,
      action_zone: 'GREEN',
      reliever_puffs: 0,
    },
    {
      id: 'c3',
      date: getVnDateOffset(3),
      checkin_time: `${getVnDateOffset(3)}T08:15:00+07:00`,
      pef_value: 455,
      pef_percent: 91,
      spo2_value: 98,
      action_zone: 'GREEN',
      reliever_puffs: 0,
    },
    {
      id: 'c2',
      date: getVnDateOffset(2),
      checkin_time: `${getVnDateOffset(2)}T07:45:00+07:00`,
      pef_value: 360,
      pef_percent: 72,
      spo2_value: 96,
      action_zone: 'YELLOW',
      reliever_puffs: 1,
    },
    {
      id: 'c1',
      date: getVnDateOffset(1),
      checkin_time: `${getVnDateOffset(1)}T08:00:00+07:00`,
      pef_value: 410,
      pef_percent: 82,
      spo2_value: 97,
      action_zone: 'GREEN',
      reliever_puffs: 0,
    },
    {
      id: 'c0',
      date: getVnDateOffset(0),
      checkin_time: `${getVnDateOffset(0)}T07:30:00+07:00`,
      pef_value: 440,
      pef_percent: 88,
      spo2_value: 98,
      action_zone: 'GREEN',
      reliever_puffs: 0,
    },
  ];
}

async function openTab(page, tabName) {
  const desktopNav = page.locator('.pw-nav-list');
  if (await desktopNav.isVisible()) {
    await desktopNav.getByRole('button', { name: tabName, exact: true }).click();
  } else {
    await page.locator('.p052-bottom-nav').getByRole('button', { name: tabName, exact: true }).click();
  }
}

async function assertNoHorizontalOverflow(page, label) {
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(
    metrics.scrollWidth,
    `${label}: horizontal overflow ${metrics.scrollWidth} > ${metrics.innerWidth}`
  ).toBeLessThanOrEqual(metrics.innerWidth);
}

test.describe('Patient Portal Responsive & Keyboard Focus Audit (AG-009)', () => {
  test('desktop scaling matrix 1024-2560px enforces max-widths, gutters, and captures AG-009 screenshots', async ({ page }) => {
    await setupResponsivePortal(page, { history: buildWeekHistory() });

    const desktopViewports = [
      { width: 1024, height: 768, shot: 'ag009-overview-1024.png' },
      { width: 1440, height: 900, shot: 'ag009-overview-1440.png' },
      { width: 1920, height: 1080, shot: 'ag009-overview-1920.png' },
      { width: 2560, height: 1440, shot: 'ag009-overview-2560.png' },
    ];

    const shellWidths = {};
    const sectionMetrics = {};

    for (const vp of desktopViewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      if (vp.width === 1024) {
        await page.goto('/');
        await expect(page.getByRole('heading', { name: /Chào / })).toBeVisible();
      }

      await openTab(page, 'Tổng quan');
      await assertNoHorizontalOverflow(page, `Overview ${vp.width}px`);

      const layout = await page.evaluate(() => {
        const shell = document.querySelector('.pw-shell')?.getBoundingClientRect();
        const grid = document.querySelector('.pw-overview-grid');
        const gridStyle = grid ? window.getComputedStyle(grid) : null;
        return {
          shellWidth: Math.round((shell?.width ?? 0) * 100) / 100,
          shellLeft: Math.round((shell?.left ?? 0) * 100) / 100,
          shellRightGutter: shell ? Math.round((window.innerWidth - shell.right) * 100) / 100 : 0,
          alignItems: gridStyle?.alignItems ?? '',
        };
      });

      shellWidths[vp.width] = layout.shellWidth;
      expect(layout.shellWidth).toBeLessThanOrEqual(1600.5);
      expect(layout.alignItems).toBe('start');
      if (vp.width >= 1920) {
        expect(layout.shellLeft).toBeGreaterThan(80);
        expect(Math.abs(layout.shellLeft - layout.shellRightGutter)).toBeLessThanOrEqual(2);
      }

      await page.evaluate(() =>
        Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {})))
      );
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: `${SCREENSHOT_DIR}/${vp.shot}` });

      await openTab(page, 'Check-in');
      await assertNoHorizontalOverflow(page, `Check-in ${vp.width}px`);
      const checkinWidth = await page.evaluate(
        () => Math.round((document.querySelector('.pw-checkin-wrap')?.getBoundingClientRect().width ?? 0) * 100) / 100
      );
      expect(checkinWidth).toBeLessThanOrEqual(960.5);
      if (vp.width === 1920) {
        await page.evaluate(() =>
          Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {})))
        );
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-checkin-1920.png` });
      }

      await openTab(page, 'Kế hoạch');
      await assertNoHorizontalOverflow(page, `Plan ${vp.width}px`);
      const planWidth = await page.evaluate(
        () => Math.round((document.querySelector('.pw-plan-wrap')?.getBoundingClientRect().width ?? 0) * 100) / 100
      );
      expect(planWidth).toBeLessThanOrEqual(1120.5);
      sectionMetrics[vp.width] = {
        shellWidth: layout.shellWidth,
        gutterLeft: layout.shellLeft,
        gutterRight: layout.shellRightGutter,
        checkinWidth,
        planWidth,
      };
      if (vp.width === 1440) {
        await page.evaluate(() =>
          Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {})))
        );
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-plan-1440.png` });
      }

      await openTab(page, 'Lịch sử');
      await assertNoHorizontalOverflow(page, `History ${vp.width}px`);
      if (vp.width === 1440) {
        await page.evaluate(() =>
          Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {})))
        );
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-history-1440.png` });
      }
    }

    expect(shellWidths[1920]).toBeGreaterThan(shellWidths[1440]);
    expect(shellWidths[1920]).toBeLessThanOrEqual(1600.5);
    expect(shellWidths[2560]).toBeLessThanOrEqual(1600.5);
    console.log('MEASURED_SECTION_METRICS:', JSON.stringify(sectionMetrics));
  });

  test('reminder action buttons fit cleanly inside card boundaries from 320px to 1440px (pending & overdue)', async ({ page }) => {
    const ackedUrls = [];
    const snoozedUrls = [];
    await setupResponsivePortal(page, {
      history: buildWeekHistory(),
      onAck: (u) => ackedUrls.push(u),
      onSnooze: (u) => snoozedUrls.push(u),
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /Chào / })).toBeVisible();

    const checkViewports = [
      { width: 1440, height: 900 },
      { width: 1024, height: 768 },
      { width: 900, height: 900 },
      { width: 768, height: 1024 },
      { width: 390, height: 844 },
      { width: 320, height: 640 },
    ];

    await openTab(page, 'Kế hoạch');

    const reminderContainment = {};
    for (const vp of checkViewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await assertNoHorizontalOverflow(page, `Plan reminders ${vp.width}px`);

      const rects = await page.evaluate(() => {
        const cards = [...document.querySelectorAll('#patient-plan-section .reminder-alert-card')];
        return cards.map((card) => {
          const style = window.getComputedStyle(card);
          const cr = card.getBoundingClientRect();
          const contentLeft = cr.left + parseFloat(style.borderLeftWidth) + parseFloat(style.paddingLeft) - 1;
          const contentRight = cr.right - parseFloat(style.borderRightWidth) - parseFloat(style.paddingRight) + 1;
          const contentTop = cr.top + parseFloat(style.borderTopWidth) + parseFloat(style.paddingTop) - 1;
          const contentBottom = cr.bottom - parseFloat(style.borderBottomWidth) - parseFloat(style.paddingBottom) + 1;
          const ack = card.querySelector('.btn-ack')?.getBoundingClientRect();
          const snooze = card.querySelector('.btn-snooze')?.getBoundingClientRect();
          const overlap =
            ack &&
            snooze &&
            !(ack.right <= snooze.left + 1 || snooze.right <= ack.left + 1 || ack.bottom <= snooze.top + 1 || snooze.bottom <= ack.top + 1);
          return {
            contentBox: { contentLeft, contentRight, contentTop, contentBottom },
            ack: ack ? { left: ack.left, right: ack.right, top: ack.top, bottom: ack.bottom, width: ack.width, height: ack.height } : null,
            snooze: snooze ? { left: snooze.left, right: snooze.right, top: snooze.top, bottom: snooze.bottom, width: snooze.width, height: snooze.height } : null,
            overlap: Boolean(overlap),
            cardScrollWidth: card.scrollWidth,
            cardClientWidth: card.clientWidth,
          };
        });
      });

      expect(rects.length).toBe(2);
      reminderContainment[vp.width] = rects.map((r) => ({
        cardWidth: r.cardClientWidth,
        ackW: Math.round((r.ack?.width ?? 0) * 10) / 10,
        snoozeW: Math.round((r.snooze?.width ?? 0) * 10) / 10,
        stackedBtns: Boolean(r.ack && r.snooze && r.snooze.top >= r.ack.bottom - 1),
      }));
      for (const r of rects) {
        expect(r.cardScrollWidth).toBeLessThanOrEqual(r.cardClientWidth + 1);
        expect(r.overlap).toBe(false);
        expect(r.ack).not.toBeNull();
        expect(r.snooze).not.toBeNull();
        for (const btn of [r.ack, r.snooze]) {
          expect(btn.left).toBeGreaterThanOrEqual(r.contentBox.contentLeft);
          expect(btn.right).toBeLessThanOrEqual(r.contentBox.contentRight);
          expect(btn.top).toBeGreaterThanOrEqual(r.contentBox.contentTop);
          expect(btn.bottom).toBeLessThanOrEqual(r.contentBox.contentBottom);
        }
      }

      if (vp.width === 320) {
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-plan-320.png` });
        await page.evaluate(() => {
          document.querySelector('#patient-plan-section .reminder-alert-card')?.scrollIntoView({ block: 'center' });
        });
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-plan-320-reminders.png` });
      }
    }

    // Verify both reminder actions remain genuinely clickable at 320px
    const firstCard = page.locator('#patient-plan-section .reminder-alert-card').first();
    await Promise.all([
      page.waitForResponse((res) => res.url().includes('/care-tracker/reminders/') && res.request().method() === 'POST'),
      firstCard.locator('.btn-snooze').click(),
    ]);
    expect(snoozedUrls.length).toBe(1);
    await Promise.all([
      page.waitForResponse((res) => res.url().includes('/care-tracker/reminders/') && res.request().method() === 'POST'),
      page.locator('#patient-plan-section .reminder-alert-card').first().locator('.btn-ack').click(),
    ]);
    expect(ackedUrls.length).toBe(1);
    console.log('MEASURED_REMINDER_CONTAINMENT:', JSON.stringify(reminderContainment));
  });

  test('mobile 390px and 320px keyboard Tab order follows DOM/visual order and avoids bottom-nav obstruction', async ({ page }) => {
    await setupResponsivePortal(page, { history: buildWeekHistory() });

    for (const vp of [
      { width: 390, height: 844, capture: true },
      { width: 320, height: 640, capture: false },
    ]) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/');
      await expect(page.getByRole('heading', { name: /Chào / })).toBeVisible();
      await assertNoHorizontalOverflow(page, `Mobile Overview ${vp.width}px`);

      if (vp.capture) {
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-overview-390.png` });
      } else {
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-overview-320.png` });
      }

      // Collect focusable elements stepped via real keyboard Tab on Overview
      await page.locator('body').focus();
      const overviewTabStops = [];
      for (let i = 0; i < 16; i += 1) {
        await page.keyboard.press('Tab');
        const info = await page.evaluate(() => {
          const el = document.activeElement;
          if (!el || el === document.body) return null;
          const rect = el.getBoundingClientRect();
          const nav = document.querySelector('.p052-bottom-nav')?.getBoundingClientRect();
          const inBottomNav = Boolean(el.closest('.p052-bottom-nav'));
          const inHiddenPanel = Boolean(el.closest('[role="tabpanel"][hidden]'));
          return {
            tag: el.tagName,
            text: (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 48),
            docTop: rect.top + window.scrollY,
            viewportBottom: rect.bottom,
            left: rect.left,
            navTop: nav?.top ?? 9999,
            inBottomNav,
            inHiddenPanel,
          };
        });
        if (!info || info.inBottomNav) {
          if (info?.inBottomNav) overviewTabStops.push(info);
          break;
        }
        overviewTabStops.push(info);
      }

      const mainStops = overviewTabStops.filter((s) => !s.inBottomNav);
      expect(mainStops.length).toBeGreaterThanOrEqual(4);
      for (const stop of mainStops) {
        expect(stop.inHiddenPanel).toBe(false);
        expect(stop.viewportBottom).toBeLessThanOrEqual(stop.navTop + 1);
      }
      for (let i = 1; i < mainStops.length; i += 1) {
        const prev = mainStops[i - 1];
        const curr = mainStops[i];
        if (Math.abs(curr.docTop - prev.docTop) <= 8) {
          expect(curr.left).toBeGreaterThanOrEqual(prev.left - 2);
        } else {
          expect(curr.docTop).toBeGreaterThanOrEqual(prev.docTop - 2);
        }
      }

      // Verify Shift+Tab moves cleanly backwards
      await page.keyboard.press('Shift+Tab');
      const afterShiftTab = await page.evaluate(() => document.activeElement?.closest('[role="tabpanel"][hidden]') !== null);
      expect(afterShiftTab).toBe(false);

      // Keyboard open HOPI from mobile top bar & Escape closes and returns focus
      const hopiBtn = page.locator('.pw-mobile-bar').getByRole('button', { name: /HOPI/i });
      await hopiBtn.focus();
      await page.keyboard.press('Enter');
      await expect(page.locator('.chat-popup')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator('.chat-popup')).toBeHidden();
      const returnedToHopi = await page.evaluate(() =>
        Boolean(document.activeElement?.getAttribute('aria-label')?.includes('HOPI'))
      );
      expect(returnedToHopi).toBe(true);

      // Plan tab: keyboard Tab + Space toggles checkbox + overflow check
      await openTab(page, 'Kế hoạch');
      await assertNoHorizontalOverflow(page, `Mobile Plan ${vp.width}px`);
      const firstCheckbox = page.locator('#patient-plan-section input[type="checkbox"]').first();
      await firstCheckbox.focus();
      await expect(firstCheckbox).not.toBeChecked();
      await page.keyboard.press('Space');
      await expect(firstCheckbox).toBeChecked();

      // History tab: keyboard Enter selects chart bar cleanly
      await openTab(page, 'Lịch sử');
      await assertNoHorizontalOverflow(page, `Mobile History ${vp.width}px`);
      const secondBar = page.locator('#patient-history-section button[aria-label*="PEF"]').nth(1);
      await secondBar.focus();
      await page.keyboard.press('Enter');
      await expect(secondBar).toHaveAttribute('aria-pressed', 'true');

      if (vp.capture) {
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-history-390.png` });

        await openTab(page, 'Check-in');
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/ag009-checkin-390.png` });
      }
    }
  });

  test('breakpoint resize preserves Check-in input, 20m timer, Plan checklist, and History selection', async ({ page }) => {
    await setupResponsivePortal(page, { history: buildWeekHistory() });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /Chào / })).toBeVisible();

    await openTab(page, 'Check-in');
    await page.locator('#pef-number-input').fill('335');
    await expect(page.getByText('VÙNG VÀNG', { exact: true })).toBeVisible();
    await expect(page.getByText(/Bộ đếm giờ an toàn 20 phút/i)).toBeVisible();

    await openTab(page, 'Kế hoạch');
    const firstCheckbox = page.locator('#patient-plan-section input[type="checkbox"]').first();
    await firstCheckbox.click();
    await expect(firstCheckbox).toBeChecked();

    await openTab(page, 'Lịch sử');
    const secondBar = page.locator('#patient-history-section button[aria-label*="PEF"]').nth(1);
    await secondBar.click();
    await expect(secondBar).toHaveAttribute('aria-pressed', 'true');

    for (const vp of [
      { width: 768, height: 1024 },
      { width: 390, height: 844 },
      { width: 1920, height: 1080 },
    ]) {
      await page.setViewportSize(vp);
      await assertNoHorizontalOverflow(page, `Resize ${vp.width}px`);
    }

    // Back at 1920px: verify all state remained intact
    await expect(page.locator('#patient-history-section button[aria-label*="PEF"]').nth(1)).toHaveAttribute('aria-pressed', 'true');
    await openTab(page, 'Kế hoạch');
    await expect(page.locator('#patient-plan-section input[type="checkbox"]').first()).toBeChecked();
    await openTab(page, 'Check-in');
    await expect(page.locator('#pef-number-input')).toHaveValue('335');
    await expect(page.getByText(/Bộ đếm giờ an toàn 20 phút/i)).toBeVisible();
  });
});
