import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

test.use({ video: 'on' });

const videoDir = path.resolve(process.cwd(), '../Evidence/W08/demo-videos');
const patientProfile = {
  patient_info: { patient_id: 'BN001', full_name: 'Nguyễn Văn An', age: 58, gender: 'Nam' },
  clinical_status: { personal_best_pef: 500, baseline_spo2: 98, diagnosis: 'Hen phế quản ngoại trú' },
  current_medications: { controller_med: 'Symbicort 160/4.5mcg', reliever_med: 'Ventolin HFA 100mcg' },
  follow_up: { hospital: 'Bệnh viện Phổi Trung ương' },
  action_plan_rules: { green_zone: 'Duy trì thuốc hằng ngày', yellow_zone: 'Theo dõi theo kế hoạch', red_zone: 'Gọi cấp cứu 115' },
};

async function preparePatientPortal(page) {
  await page.route('**/api/v1/auth/me', route => route.fulfill({
    json: { id: 'patient-1', username: 'patient1', full_name: patientProfile.patient_info.full_name, role: 'patient', patient_id: 'BN001' },
  }));
  await page.route('**/api/v1/patients/*', route => {
    if (route.request().url().endsWith('/patients/')) {
      return route.fulfill({ json: [{ patient_id: 'BN001', full_name: 'Nguyễn Văn An', age: 58, personal_best_pef: 500 }] });
    }
    return route.fulfill({ json: patientProfile });
  });
  await page.route('**/api/v1/care-tracker/care-plans/**', route => route.fulfill({
    json: { patient_id: 'BN001', personal_best_pef: 500, baseline_spo2: 98, items: [
      { id: 'med-1', item_type: 'CONTROLLER_MED', title: 'Symbicort 160/4.5mcg', dosage: '1 nhát x 2 lần/ngày', instructions: 'Súc miệng sau khi xịt', schedule_times: ['07:00', '19:00'] },
    ] },
  }));
  await page.route('**/api/v1/care-tracker/checkin/**', route => route.fulfill({
    json: route.request().method() === 'POST'
      ? { id: 'checkin-demo', action_zone: 'GREEN', patient_id: 'BN001' }
      : [],
  }));
  await page.route('**/api/v1/care-tracker/reminders/active/**', route => route.fulfill({ json: [] }));
  await page.route('**/api/v1/screener/evaluate', route => route.fulfill({
    json: { safety_status: 'GREEN_ZONE', risk_score: 0, matched_reasons: ['Chỉ số ổn định'], action_instructions: 'Tiếp tục theo dõi và dùng thuốc theo kế hoạch.' },
  }));
  await page.route('**/api/v1/chat/conversations*', route => route.fulfill({ json: [] }));
}

async function saveVideo(page, filename) {
  fs.mkdirSync(videoDir, { recursive: true });
  const video = page.video();
  await page.close();
  await video.saveAs(path.join(videoDir, filename));
}

test('demo video: patient overview and daily check-in', async ({ page }) => {
  await preparePatientPortal(page);
  await page.goto('/');
  await expect(page.locator('#patient-overview-section')).toBeVisible();
  await expect(page.getByText('Chào Nguyễn Văn An')).toBeVisible();
  await page.waitForTimeout(1000);
  await page.locator('.pw-sidebar').getByRole('button', { name: 'Check-in', exact: true }).click();
  await expect(page.locator('#patient-checkin-section')).toBeVisible();
  await page.locator('#pef-number-input').fill('465');
  await page.getByRole('button', { name: 'Lưu đánh giá hôm nay' }).click();
  await expect(page.getByText('Đã lưu đánh giá sức khỏe hôm nay thành công!')).toBeVisible();
  await page.waitForTimeout(1000);
  await saveVideo(page, '01-patient-dashboard-checkin.webm');
});

test('demo video: patient asks HOPI for help', async ({ page }) => {
  await preparePatientPortal(page);
  await page.route('**/api/v1/chat/chat', async route => route.fulfill({
    json: {
      response: 'Bác hãy dùng thuốc đúng theo kế hoạch điều trị và liên hệ cơ sở y tế nếu triệu chứng nặng lên.',
      safety_status: 'NORMAL', citations: [], conversation_id: 'conversation-demo', message_id: 'message-demo',
    },
  }));
  await page.goto('/');
  await expect(page.locator('#patient-overview-section')).toBeVisible();
  await page.waitForTimeout(700);
  await page.getByRole('button', { name: 'Hỏi trợ lý HOPI' }).click();
  await expect(page.locator('.chat-popup')).toBeVisible();
  await page.getByRole('textbox', { name: 'Tin nhắn cho trợ lý' }).fill('Tôi nên làm gì để theo dõi cơn hen tại nhà?');
  await page.getByRole('button', { name: 'Gửi tin nhắn' }).click();
  await expect(page.locator('.chat-bubble').filter({ hasText: 'Bác hãy dùng thuốc đúng theo kế hoạch' })).toBeVisible();
  await page.waitForTimeout(1000);
  await saveVideo(page, '02-patient-hopi-chat.webm');
});
