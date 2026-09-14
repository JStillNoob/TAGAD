import { existsSync, mkdirSync, rmSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const frontendDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryDirectory = path.resolve(frontendDirectory, '..')
const backendDirectory = path.join(repositoryDirectory, 'backend')
const e2eDirectory = path.join(backendDirectory, '.e2e')
const resultDirectory = path.join(frontendDirectory, '.e2e-results')
const python = process.env.TAGAD_E2E_PYTHON || (
  process.platform === 'win32'
    ? path.join(backendDirectory, 'venv', 'Scripts', 'python.exe')
    : path.join(backendDirectory, 'venv', 'bin', 'python')
)
const playwrightCli = path.join(frontendDirectory, 'node_modules', '@playwright', 'test', 'cli.js')
const environment = {
  ...process.env,
  DJANGO_SETTINGS_MODULE: 'tagad.e2e_settings',
  SECRET_KEY: 'e2e-only-secret-key-not-for-production',
  DB_NAME: 'unused-e2e-database',
  DB_USER: 'unused-e2e-user',
  DB_PASSWORD: 'unused-e2e-password',
  DB_HOST: '127.0.0.1',
  DB_PORT: '5432',
  DJANGO_DEBUG: 'true',
  TAGAD_E2E_PYTHON: python,
}

function removeKnownDirectory(target, expectedParent) {
  if (path.dirname(target) !== expectedParent) {
    throw new Error(`Refusing to clean unexpected E2E path: ${target}`)
  }
  rmSync(target, { recursive: true, force: true })
}

function run(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    env: environment,
    stdio: 'inherit',
  })
  if (result.error) throw result.error
  if (result.status !== 0) process.exit(result.status ?? 1)
}

if (!existsSync(python)) {
  throw new Error(
    `Python virtual environment was not found at ${python}. `
    + 'Create backend/venv or set TAGAD_E2E_PYTHON.',
  )
}

removeKnownDirectory(e2eDirectory, backendDirectory)
removeKnownDirectory(resultDirectory, frontendDirectory)
mkdirSync(e2eDirectory)

run(python, ['manage.py', 'migrate', '--noinput', '--settings=tagad.e2e_settings'], backendDirectory)
run(python, ['manage.py', 'prepare_e2e', '--settings=tagad.e2e_settings'], backendDirectory)
run(process.execPath, [playwrightCli, 'test'], frontendDirectory)
