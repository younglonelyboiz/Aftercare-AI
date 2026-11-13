import { test, expect } from '@playwright/test';

const mockPatientProfile = {
  patient_info: {
    patient_id: 'BN-2026-ASTHMA-01',
    full_name: 'Nguyễn Văn An',
    age: 28,
    gender: 'Nam',
    discharge_date: '2026-10-01'
  },
  clinical_status: {
    diagnosis: 'Hen phế quản nhẹ - Đã kiểm soát tốt',
    known_triggers: ['Phấn hoa', 'Khói bụi đường phố'],
    personal_best_pef: 520,
    baseline_spo2: 98
  },
  current_medications: {
    controller_med: 'Không dùng thuốc duy trì hàng ngày (Bậc 1).',
    reliever_med: 'Budesonide/Formoterol 80/4.5mcg xịt khi có triệu chứng.'
  },
  follow_up: {
    next_appointment: '2026-12-01',
    hospital: 'Bệnh viện Phổi Trung ương'
  },
  action_plan_rules: {
    green_zone: 'TÌNH TRẠNG HIỆN TẠI ỔN ĐỊNH',
    yellow_zone: 'CẢNH BÁO HEN TRỞ NẶNG',
    red_zone: 'CẢNH BÁO CỜ ĐỎ CẤP CỨU'
  }
};

const mockCarePlan = {
  id: 'plan-BN-2026-ASTHMA-01',
  patient_id: 'BN-2026-ASTHMA-01',
  personal_best_pef: 520,
  baseline_spo2: 98,
  items: [
    {
      id: 'item-1',
      item_type: 'CONTROLLER_MED',
      title: 'Xịt Symbicort 160/4.5mcg',
      dosage: '2 nhát/lần',
      instructions: 'Hít sâu qua buồng đệm, súc miệng nước ấm sạch',
      schedule_times: ['08:00', '20:00'],
      is_active: true
    },
    {
      id: 'item-2',
      item_type: 'PEF_MEASURE',
      title: 'Đo lưu lượng đỉnh (PEF) buổi sáng',
      dosage: 'Thổi 3 lần',
      instructions: 'Đo lúc mới thức dậy trước khi vận động',
      schedule_times: ['07:30'],
      is_active: true
    }
  ]
};

async function setupPatientMock(page) {
  await page.route('https://fonts.googleapis.com/**', route => route.abort());

  await page.route('**/api/v1/auth/me', route => route.fulfill({
    status: 200,
    json: {
      id: 1,
      username: 'patient1',
      role: 'patient',
      full_name: 'Nguyễn Văn An',
      patient_id: 'BN-2026-ASTHMA-01'
    }
  }));

  await page.route('**/api/v1/patients/', route => route.fulfill({
    status: 200,
    json: [mockPatientProfile]
  }));

  await page.route('**/api/v1/patients/BN-2026-ASTHMA-01', route => route.fulfill({
    status: 200,
    json: mockPatientProfile
  }));

  await page.route('**/api/v1/care-plans/BN-2026-ASTHMA-01', route => route.fulfill({
    status: 200,
    json: mockCarePlan
  }));

  await page.route('**/api/v1/care-tracker/checkin/history/**', route => route.fulfill({
    status: 200,
    json: [
      { date: '2026-11-08', pef_value: 480, spo2_value: 98, action_zone: 'GREEN', reliever_puffs: 0 },
      { date: '2026-11-07', pef_value: 390, spo2_value: 96, action_zone: 'YELLOW', reliever_puffs: 2 }
    ]
  }));

  await page.route('**/api/v1/care-tracker/reminders/active/**', route => route.fulfill({
    status: 200,
    json: []
  }));

  await page.route('**/api/v1/conversations?patient_id=BN-2026-ASTHMA-01', route => route.fulfill({
    status: 200,
    json: []
  }));

  await page.route('**/api/v1/screener/evaluate', route => route.fulfill({
    status: 200,
    json: {
      risk_level: 'NORMAL',
      matched_flags: [],
      matched_reasons: ['Chỉ số an toàn bình thường.'],
      action_instructions: 'Tiếp tục duy trì phác đồ.'
    }
  }));
}

test.describe('Patient Portal P052 Style', () => {
  test('Renders desktop patient portal with 3 clinical cards and retains input across tab switch', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await setupPatientMock(page);

    await page.goto('/');

    // Verify welcome greeting on default Overview tab
    await expect(page.getByText('Chào Nguyễn Văn An')).toBeVisible();

    // Navigate to Check-in tab where the 3 clinical cards live
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();
    await expect(page.getByText('Khảo Sát Kiểm Soát Hen Hằng Ngày')).toBeVisible();

    // Verify 3 distinct cards are present in Check-in tab
    await expect(page.getByText('1. Sinh Hiệu Hô Hấp Buổi Sáng')).toBeVisible();
    await expect(page.getByText('2. Triệu Chứng Trong 24 Giờ Qua')).toBeVisible();
    await expect(page.getByText('3. Đánh Giá Phân Tầng An Toàn')).toBeVisible();

    // Fill PEF input to 410
    const pefInput = page.locator('#pef-number-input');
    await pefInput.fill('410');
    await expect(pefInput).toHaveValue('410');

    // Switch to History tab
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Lịch sử', exact: true }).click();
    await expect(page.getByText('Nhật Ký & Xu Hướng Kiểm Soát Hen (14 Ngày)')).toBeVisible();

    // Switch back to Check-in tab
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();

    // Verify PEF value was NOT lost
    await expect(pefInput).toHaveValue('410');
  });

  test('Submitting check-in sends POST request with correct payload', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await setupPatientMock(page);

    // Accept window.alert automatically
    page.on('dialog', dialog => dialog.accept());

    let checkinPayload = null;
    await page.route('**/api/v1/care-tracker/checkin/**', async (route) => {
      if (route.request().method() === 'POST') {
        checkinPayload = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          json: {
            id: 'checkin-1',
            patient_id: 'BN-2026-ASTHMA-01',
            action_zone: 'GREEN',
            pef_value: 450
          }
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/');

    // Open Check-in tab
    await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();

    // Change PEF to 450
    const pefInput = page.locator('#pef-number-input');
    await pefInput.fill('450');

    // Toggle symptom "Tỉnh giấc ban đêm"
    await page.getByRole('button', { name: /Tỉnh giấc ban đêm/i }).click();

    // Click "Lưu đánh giá hôm nay"
    await page.getByRole('button', { name: 'Lưu đánh giá hôm nay' }).click();

    // Wait until payload is captured
    await expect.poll(() => checkinPayload).not.toBeNull();
    expect(checkinPayload.pef_value).toBe(450);
    expect(checkinPayload.symptoms?.nightWaking).toBe(true);

    // Verify success banner appears
    await expect(page.getByText('Đã lưu đánh giá sức khỏe hôm nay thành công!')).toBeVisible();
  });

  test('Renders mobile layout without horizontal overflow at 390px', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await setupPatientMock(page);

    await page.goto('/');

    // Verify bottom nav (4 tabs) is visible on mobile and HOPI stays in mobile header
    const bottomNav = page.locator('.p052-bottom-nav');
    await expect(bottomNav).toBeVisible();
    await expect(bottomNav.locator('button')).toHaveCount(4);
    await expect(page.locator('.pw-mobile-bar').getByRole('button', { name: 'Hỏi trợ lý HOPI' })).toBeVisible();

    // Verify document does not have horizontal overflow
    const isOverflowing = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(isOverflowing).toBe(false);
  });
});
