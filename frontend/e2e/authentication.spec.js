import { accounts, expect, login, logout, test } from './support.js'


test('registration, login, logout, and password recovery use real browser navigation', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Register' }).click()
  await expect(page).toHaveURL(/\/register$/)

  await page.getByLabel('First Name').fill('Browser')
  await page.getByLabel('Last Name').fill('Registrant')
  await page.getByLabel('Username').fill('e2e.registrant')
  await page.getByLabel('Email Address').fill('e2e.registrant@example.test')
  await page.getByLabel('Organization Code').fill('E2E-SCHOOL')
  await page.getByLabel('Password', { exact: true }).fill('Zebra!Cloud#4827')
  await page.getByLabel('Confirm Password').fill('Zebra!Cloud#4827')
  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page).toHaveURL(/\/?registered=1$/)
  await expect(page.getByRole('status')).toContainText('Account created successfully')
  await page.getByLabel('Email or Username').fill('e2e.registrant')
  await page.getByLabel('Password').fill('Zebra!Cloud#4827')
  await page.locator('form').getByRole('button', { name: 'Start Session' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await logout(page)

  await page.getByRole('link', { name: 'Forgot password?' }).click()
  await expect(page).toHaveURL(/\/forgot-password$/)
  await page.getByLabel('Email address').fill('e2e.registrant@example.test')
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible()
  await expect(page.getByText('If an active account matches that email')).toBeVisible()
})

test('seeded teacher can sign in and sign out', async ({ page }) => {
  await login(page, accounts.teacher)
  await logout(page)
})

test('repeated failed sign-ins are restricted without blocking another identity', async ({ page }) => {
  await page.goto('/')
  for (let attempt = 0; attempt < 5; attempt += 1) {
    await page.getByLabel('Email or Username').fill('e2e.missing')
    await page.getByLabel('Password').fill('WrongPassword!9')
    await page.locator('form').getByRole('button', { name: 'Start Session' }).click()
    await expect(page.getByRole('alert')).toContainText('Invalid credentials')
  }

  await page.locator('form').getByRole('button', { name: 'Start Session' }).click()
  await expect(page.getByRole('alert')).toContainText('Too many sign-in attempts')

  await page.getByLabel('Email or Username').fill(accounts.systemAdmin)
  await page.getByLabel('Password').fill('BrowserTest!2026')
  await page.locator('form').getByRole('button', { name: 'Start Session' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
})

test('repeated password-reset requests show a generic temporary restriction', async ({ page }) => {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await page.goto('/forgot-password')
    await page.getByLabel('Email address').fill('e2e.missing@example.test')
    await page.getByRole('button', { name: 'Send reset link' }).click()
    await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible()
  }

  await page.goto('/forgot-password')
  await page.getByLabel('Email address').fill('e2e.missing@example.test')
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await expect(page.getByRole('alert')).toContainText('Too many password-reset requests')
})
