import { accounts, createMinimalPdf, expect, login, logout, test } from './support.js'


test('teacher uploads, refreshes an active session, simulates data, reports, and logs out', async ({ page }, testInfo) => {
  const pdfPath = testInfo.outputPath('browser-presentation.pdf')
  await createMinimalPdf(pdfPath)
  await login(page, accounts.teacher)

  await page.getByRole('link', { name: 'Live Session' }).click()
  await expect(page).toHaveURL(/\/session$/)
  await page.getByLabel('Title').fill('E2E Session Slides')
  await page.getByLabel('File').setInputFiles(pdfPath)
  await page.getByRole('button', { name: 'Upload Presentation' }).click()
  await expect(page.getByText('E2E Session Slides', { exact: true })).toBeVisible()
  await expect(page.getByText('1 generated slides')).toBeVisible()

  const sessionDetails = page.getByRole('heading', { name: 'Session Details' }).locator('..')
  const subjectSelect = sessionDetails.locator('select').nth(0)
  const subjectValue = await subjectSelect.locator('option').filter({ hasText: 'E2E-IT101' }).getAttribute('value')
  await subjectSelect.selectOption(subjectValue)
  const presentationSelect = sessionDetails.locator('select').nth(1)
  const presentationValue = await presentationSelect.locator('option').filter({ hasText: 'E2E Session Slides' }).getAttribute('value')
  await presentationSelect.selectOption(presentationValue)
  await page.getByRole('button', { name: 'Start Session', exact: true }).click()
  await expect(page.getByRole('button', { name: 'End Session' })).toBeVisible()
  await expect(page.getByText('Slide 1 of 1')).toBeVisible()

  await page.reload()
  await expect(page.getByRole('button', { name: 'End Session' })).toBeVisible()
  await expect(page.getByText('Slide 1 of 1')).toBeVisible()
  await page.getByRole('button', { name: 'Start Simulation' }).click()
  await expect(page.getByRole('button', { name: 'Stop Simulation' })).toBeVisible()
  await expect(page.getByText(/detected · \d+ unclassified · Slide 1/)).toBeVisible()

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'End Session' }).click()
  await expect(page).toHaveURL(/\/analytics\?session=\d+$/)
  await expect(page.getByText('Students Detected')).toBeVisible()

  await page.getByRole('link', { name: 'Reports' }).click()
  await page.getByRole('button', { name: 'Generate polished PDF' }).click()
  await expect(page.getByRole('status')).toContainText('Polished PDF report generated successfully')
  await expect(page.getByText('Session Summary', { exact: true })).toBeVisible()
  await logout(page)
})
