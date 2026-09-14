import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const frontendDirectory = path.dirname(fileURLToPath(import.meta.url))
const backendDirectory = path.resolve(frontendDirectory, '../backend')
const python = process.env.TAGAD_E2E_PYTHON || (
  process.platform === 'win32'
    ? path.join(backendDirectory, 'venv', 'Scripts', 'python.exe')
    : path.join(backendDirectory, 'venv', 'bin', 'python')
)

export default defineConfig({
  testDir: './e2e',
  outputDir: './.e2e-results',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: [['line']],
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'off',
    video: 'off',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: `"${python}" manage.py runserver 127.0.0.1:8001 --settings=tagad.e2e_settings --noreload`,
      cwd: backendDirectory,
      url: 'http://127.0.0.1:8001/api/auth/csrf/',
      reuseExistingServer: false,
      timeout: 30_000,
      env: process.env,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: frontendDirectory,
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        ...process.env,
        VITE_BACKEND_TARGET: 'http://127.0.0.1:8001',
      },
    },
  ],
})
