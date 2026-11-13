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


test('today owns actions, record owns reference, HOPI and checkin persist on mobile', async ({ page }) => {
 await setupAg011Portal(page);
 let actions = [];
 await page.route('**/api/v1/care-tracker/reminders/*/action', async route => {
   actions.push(route.request().postDataJSON());
   await route.fulfill({json:{success:true}});
 });
 await page.goto('/?tab=overview');
 await expect(page.locator('#patient-overview-section .btn-ack')).toBeVisible();
 await page.locator('#patient-overview-section .btn-snooze').click();
 await expect.poll(()=>actions.length).toBe(1);
 await expect(page.locator('#patient-overview-section .btn-ack')).toHaveCount(0);
 await page.reload();
 await page.locator('#patient-overview-section .btn-ack').click();
 await expect.poll(()=>actions.length).toBe(2);
 await page.locator('.pw-nav-btn').filter({hasText:'Hồ sơ & Kế hoạch'}).click();
 await expect(page.locator('#patient-plan-section')).toBeVisible();
 await expect(page.locator('#patient-plan-section .reminder-alert-card')).toHaveCount(0);
 await expect(page.getByText('Hồ Sơ Xuất Viện & Kế Hoạch Cá Nhân')).toBeVisible();
 await page.locator('.pw-nav-btn').filter({hasText:'Check-in'}).click();
 await page.locator('#pef-number-input').fill('430');
 await page.setViewportSize({width:390,height:844});
 await page.locator('.p052-bottom-nav button').filter({hasText:'Hôm nay'}).click();
 const fab=page.locator('.hopi-patient-launcher');
 await expect(fab).toBeVisible();
 const f=await fab.boundingBox(), n=await page.locator('.p052-bottom-nav').boundingBox();
 expect(f.y+f.height).toBeLessThan(n.y);
 await fab.click();
 await expect(page.locator('.chat-popup')).toBeVisible();
 await page.keyboard.press('Escape');
 await expect(page.locator('.chat-popup')).toHaveCount(0);
 await page.locator('.p052-bottom-nav button').filter({hasText:'Check-in'}).click();
 await expect(page.locator('#pef-number-input')).toHaveValue('430');
 for(const width of [320,390,768,1440,1920]){
   await page.setViewportSize({width,height:900});
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
 await page.goto('/?tab=overview');
 await page.screenshot({path:'/tmp/aftercare-today-1920.png'});
});

