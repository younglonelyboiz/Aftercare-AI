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

async function setupAg011Portal(page) {
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

  const reminders = [
    {
      id: 'rem-1',
      title: 'Đến giờ xịt Symbicort buổi tối',
      message_content: 'Hãy hít 1 nhát duy trì và súc miệng sạch sau khi dùng.',
      scheduled_time: '19:00',
      status: 'PENDING',
      is_overdue: false,
      reminder_type: 'MEDICATION',
    },
  ];

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

  await page.route('**/api/v1/care-tracker/care-plans/**', async (route) => route.fulfill({ json: carePlan }));
  await page.route('**/api/v1/care-tracker/checkin/**', async (route) => {
    if (route.request().url().includes('/checkin/history/')) return route.fulfill({ json: history });
    return route.fulfill({ json: { id: 'ok' } });
  });
  await page.route('**/api/v1/care-tracker/reminders/active/**', async (route) => route.fulfill({ json: reminders }));
  await page.route('**/api/v1/chat/conversations*', async (route) => route.fulfill({ json: [] }));
  await page.route('**/api/v1/screener/evaluate', async (route) => {
    const pef = Number(route.request().postDataJSON()?.pef_value ?? 450);
    await route.fulfill({
      json: pef < 400
        ? { safety_status: 'YELLOW_ZONE', risk_score: 2, matched_reasons: ['PEF 67% mức tốt nhất'], action_instructions: 'Dùng thuốc cắt cơn.' }
        : { safety_status: 'GREEN_ZONE', risk_score: 0, matched_reasons: ['Chỉ số an toàn'], action_instructions: 'Tiếp tục duy trì.' },
    });
  });
}

test.describe('Patient Portal Cleanup & URL Sync (AG-011)', () => {
  test('syncs tabs with ?tab= URL query, supports reload/invalid fallback, History Back/Forward, and preserves state', async ({ page }) => {
    await setupAg011Portal(page);
    await page.setViewportSize({ width: 1440, height: 900 });

    // 1. Deep-link + reload for history tab
    await page.goto('/?tab=history');
    await expect(page.locator('#patient-history-section')).toBeVisible();
    await expect(page.locator('#patient-overview-section')).toBeHidden();
    await page.reload();
    await expect(page.locator('#patient-history-section')).toBeVisible();
    expect(new URL(page.url()).searchParams.get('tab')).toBe('history');

    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag011-history-deeplink-1440.png` });

    // 2. Deep-link plan and checkin
    await page.goto('/?tab=plan');
    await expect(page.locator('#patient-plan-section')).toBeVisible();
    await page.goto('/?tab=checkin');
    await expect(page.locator('#patient-checkin-section')).toBeVisible();

    // 3. Invalid tab falls back to overview
    await page.goto('/?tab=does-not-exist');
    await expect(page.locator('#patient-overview-section')).toBeVisible();
    await expect.poll(() => new URL(page.url()).searchParams.get('tab')).toBe('overview');

    await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
    await page.screenshot({ path: `${SCREENSHOT_DIR}/ag011-overview-1440.png` });

    // 4. Interactive navigation updates URL and Back/Forward preserves form, timer, checklist, and chart state
    const nav = page.locator('.pw-nav-list');
    await nav.getByRole('button', { name: 'Check-in', exact: true }).click();
    expect(new URL(page.url()).searchParams.get('tab')).toBe('checkin');
    await page.locator('#pef-number-input').fill('335');
    await expect(page.getByText(/Bộ đếm giờ an toàn 20 phút/i)).toBeVisible();

    await nav.getByRole('button', { name: 'Kế hoạch', exact: true }).click();
    expect(new URL(page.url()).searchParams.get('tab')).toBe('plan');
    const firstCheckbox = page.locator('#patient-plan-section input[type="checkbox"]').first();
    await firstCheckbox.click();
    await expect(firstCheckbox).toBeChecked();

    await nav.getByRole('button', { name: 'Lịch sử', exact: true }).click();
    expect(new URL(page.url()).searchParams.get('tab')).toBe('history');
    const secondBar = page.locator('#patient-history-section button[aria-label*="PEF"]').nth(1);
    await secondBar.click();
    await expect(secondBar).toHaveAttribute('aria-pressed', 'true');

    // Back -> plan -> checkin
    await page.goBack();
    await expect(page.locator('#patient-plan-section')).toBeVisible();
    expect(new URL(page.url()).searchParams.get('tab')).toBe('plan');
    await expect(firstCheckbox).toBeChecked();

    await page.goBack();
    await expect(page.locator('#patient-checkin-section')).toBeVisible();
    expect(new URL(page.url()).searchParams.get('tab')).toBe('checkin');
    await expect(page.locator('#pef-number-input')).toHaveValue('335');
    await expect(page.getByText(/Bộ đếm giờ an toàn 20 phút/i)).toBeVisible();

    // Forward -> plan -> history
    await page.goForward();
    await expect(page.locator('#patient-plan-section')).toBeVisible();
    await expect(firstCheckbox).toBeChecked();

    await page.goForward();
    await expect(page.locator('#patient-history-section')).toBeVisible();
    await expect(secondBar).toHaveAttribute('aria-pressed', 'true');
  });

  test('patient portal images define explicit width/height and mobile bottom nav clears bottom content/focus at 320, 390, 768px', async ({ page }) => {
    await setupAg011Portal(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/?tab=overview');
    await expect(page.locator('#patient-overview-section')).toBeVisible();

    // Verify explicit dimensions on all patient portal images
    const imgAudit = await page.evaluate(() => {
      const imgs = [...document.querySelectorAll('.portal-patient img')];
      return imgs.map((img) => ({
        alt: img.getAttribute('alt') || '',
        widthAttr: img.getAttribute('width'),
        heightAttr: img.getAttribute('height'),
        naturalWidth: img.naturalWidth,
        complete: img.complete,
      }));
    });
    expect(imgAudit.length).toBeGreaterThanOrEqual(3);
    for (const img of imgAudit) {
      expect(Number(img.widthAttr), `img "${img.alt}" missing numeric width`).toBeGreaterThan(0);
      expect(Number(img.heightAttr), `img "${img.alt}" missing numeric height`).toBeGreaterThan(0);
      expect(img.complete).toBe(true);
      expect(img.naturalWidth).toBeGreaterThan(0);
    }

    // Check bottom nav clearance across 768x1024, 390x844, 320x640
    for (const vp of [
      { width: 768, height: 1024, shot: null },
      { width: 390, height: 844, shot: 'ag011-mobile-390.png' },
      { width: 320, height: 640, shot: 'ag011-mobile-320.png' },
    ]) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.evaluate(() => window.scrollTo(0, 0));

      const navButtonsClear = await page.evaluate(() => {
        const nav = document.querySelector('.p052-bottom-nav')?.getBoundingClientRect();
        const btns = [...document.querySelectorAll('.p052-bottom-nav button')];
        return {
          navTop: nav?.top ?? 0,
          navHeight: nav?.height ?? 0,
          buttonCount: btns.length,
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
        };
      });
      expect(navButtonsClear.buttonCount).toBe(4);
      expect(navButtonsClear.scrollWidth).toBeLessThanOrEqual(navButtonsClear.innerWidth);

      if (vp.shot) {
        await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished.catch(() => {}))));
        await page.screenshot({ path: `${SCREENSHOT_DIR}/${vp.shot}` });
      }

      // Check every tab at scroll bottom clears .p052-bottom-nav completely
      for (const tabBtn of ['Tổng quan', 'Check-in', 'Kế hoạch', 'Lịch sử']) {
        await page.locator('.p052-bottom-nav').getByRole('button', { name: tabBtn, exact: true }).click();
        await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
        const clearance = await page.evaluate(() => {
          const nav = document.querySelector('.p052-bottom-nav')?.getBoundingClientRect();
          const shell = document.querySelector('.pw-shell')?.getBoundingClientRect();
          return {
            shellBottom: shell?.bottom ?? 9999,
            navTop: nav?.top ?? 0,
          };
        });
        expect(
          clearance.shellBottom,
          `${vp.width}px tab ${tabBtn}: shell bottom ${clearance.shellBottom} overlaps navTop ${clearance.navTop}`
        ).toBeLessThanOrEqual(clearance.navTop + 1);
      }

      // Also verify at 768x1024 Overview scrollY=0 (fits within single screen) does not hit nav
      if (vp.width === 768) {
        await page.locator('.p052-bottom-nav').getByRole('button', { name: 'Tổng quan', exact: true }).click();
        await page.evaluate(() => window.scrollTo(0, 0));
        const fitCheck = await page.evaluate(() => {
          const nav = document.querySelector('.p052-bottom-nav')?.getBoundingClientRect();
          const lastCard = document.querySelector('#patient-overview-section .pw-overview-next-card')?.getBoundingClientRect();
          return { lastCardBottom: lastCard?.bottom ?? 9999, navTop: nav?.top ?? 0 };
        });
        expect(fitCheck.lastCardBottom).toBeLessThanOrEqual(fitCheck.navTop + 1);
      }

      // Keyboard Tab down to the bottom interactive element in Overview stays above bottom nav
      await page.locator('.p052-bottom-nav').getByRole('button', { name: 'Tổng quan', exact: true }).click();
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.locator('body').focus();
      for (let i = 0; i < 14; i += 1) {
        await page.keyboard.press('Tab');
        const check = await page.evaluate(() => {
          const el = document.activeElement;
          if (!el || el === document.body || el.closest('.p052-bottom-nav')) return { done: true, ok: true };
          const r = el.getBoundingClientRect();
          const nav = document.querySelector('.p052-bottom-nav')?.getBoundingClientRect();
          return { done: false, ok: r.bottom <= (nav?.top ?? 9999) + 1 };
        });
        expect(check.ok).toBe(true);
        if (check.done) break;
      }
    }
  });
});
