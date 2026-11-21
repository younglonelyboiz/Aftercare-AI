import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/ui',
  testMatch: 'backend-live-e2e.spec.js',
  globalTeardown: './tests/backend-live-teardown.js',
  fullyParallel: false,
  workers: 1,
  timeout: 150000,
  use: { baseURL: 'http://127.0.0.1:5174', browserName: 'chromium', timezoneId: 'Asia/Ho_Chi_Minh', trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'python -m uvicorn backend.app.testing.live_e2e:app --host 127.0.0.1 --port 8011',
      url: 'http://127.0.0.1:8011/',
      cwd: '..',
      reuseExistingServer: false,
      timeout: 30000,
      env: { PYTHONPATH: '..' },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
      timeout: 30000,
      env: { VITE_API_URL: 'http://127.0.0.1:8011/api/v1' },
    },
  ],
});
