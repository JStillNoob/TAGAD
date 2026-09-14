import { accounts, expect, login, test } from './support.js'


test('organization administrator manages a user and completes Quick Setup', async ({ page }) => {
  await login(page, accounts.organizationAdmin)

  await page.getByRole('link', { name: 'User Management' }).click()
  await expect(page).toHaveURL(/\/users$/)
  await page.getByRole('button', { name: 'Add User' }).click()
  const userDialog = page.getByRole('dialog', { name: 'Add User' })
  await userDialog.getByLabel('First name').fill('Browser')
  await userDialog.getByLabel('Last name').fill('Managed Teacher')
  await userDialog.getByLabel('Username').fill('e2e.managed.teacher')
  await userDialog.getByLabel('Email address').fill('e2e.managed.teacher@example.test')
  await userDialog.getByLabel('Password').fill('Orbit!Stone#5931')
  await userDialog.getByRole('button', { name: 'Create User' }).click()
  await expect(userDialog).toBeHidden()
  await expect(page.getByText('e2e.managed.teacher', { exact: false })).toBeVisible()

  await page.getByRole('link', { name: 'Classes' }).click()
  await expect(page.getByText('E2E Front Camera', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Quick Setup' }).click()
  const setupDialog = page.getByRole('dialog', { name: 'Quick Classroom Setup' })
  await setupDialog.getByRole('button', { name: 'Create new' }).click()
  await setupDialog.getByLabel('Room code').fill('E2E-202')
  await setupDialog.getByLabel('Building').fill('Browser Test Wing')
  await setupDialog.getByLabel('Capacity').fill('24')
  await setupDialog.getByLabel('Subject code').fill('E2E-QS202')
  await setupDialog.getByLabel('Subject name').fill('Reliable Browser Journeys')
  await setupDialog.getByLabel('Teacher').selectOption({ label: 'E2E Teacher' })
  await setupDialog.getByRole('button', { name: 'Complete Setup' }).click()

  await expect(setupDialog).toBeHidden()
  await expect(page.getByText('E2E-QS202', { exact: true })).toBeVisible()
  await expect(page.getByText('E2E-202', { exact: true }).first()).toBeVisible()
})

for (const [role, identity, allowed] of [
  ['system administrator', accounts.systemAdmin, true],
  ['organization administrator', accounts.organizationAdmin, true],
  ['teacher', accounts.teacher, false],
]) {
  test(`${role} receives the correct User Management navigation permission`, async ({ page }) => {
    await login(page, identity)
    await page.goto('/users')
    if (allowed) {
      await expect(page).toHaveURL(/\/users$/)
      await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible()
    } else {
      await expect(page).toHaveURL(/\/dashboard$/)
      await expect(page.getByRole('link', { name: 'User Management' })).toHaveCount(0)
    }
  })
}

test('an unauthenticated user is redirected away from protected pages', async ({ page }) => {
  await page.goto('/reports')
  await expect(page).toHaveURL(/\/?redirect=(?:%2F|\/)reports$/)
  await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()
})
