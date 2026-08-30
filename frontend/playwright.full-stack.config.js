import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  testMatch: '**/full-stack.spec.js',
  outputDir: './test-results/full-stack',
  reporter: 'line',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv run python app/manage.py runserver 127.0.0.1:8000',
      cwd: '..',
      url: 'http://127.0.0.1:8000/health/',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
    },
  ],
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
