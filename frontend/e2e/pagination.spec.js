import { accounts, expect, login, test } from './support.js'


test('growing lists navigate to page two without crossing organization scope', async ({ page }) => {
  await login(page, accounts.organizationAdmin)

  await page.getByRole('link', { name: 'User Management' }).click()
  await expect(page.getByText(/2[2-4] results · Page 1 of 2/)).toBeVisible()
  await page.getByRole('button', { name: 'Next' }).click()
  await expect(page.getByText(/2[2-4] results · Page 2 of 2/)).toBeVisible()
  await expect(page.getByText('e2e.scale.teacher.021', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Previous' }).click()
  await expect(page.getByText(/2[2-4] results · Page 1 of 2/)).toBeVisible()
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByPlaceholder('Search name, username, or email…').fill('e2e.scale.teacher.021')
  await expect(page.getByText('1 result · Page 1 of 1')).toBeVisible()

  await page.getByRole('link', { name: 'Classes', exact: true }).click()
  const subjects = page.locator('#subjects-panel')
  await expect(subjects.getByText(/2[2-3] results · Page 1 of 2/)).toBeVisible()
  await subjects.getByRole('button', { name: 'Next' }).click()
  await expect(subjects.getByText(/2[2-3] results · Page 2 of 2/)).toBeVisible()
  await expect(subjects.getByText('E2E-SUBJECT-021', { exact: true })).toBeVisible()
  await subjects.getByRole('button', { name: 'Previous' }).click()
  await expect(subjects.getByText(/2[2-3] results · Page 1 of 2/)).toBeVisible()

  await page.getByRole('tab', { name: /Classrooms/ }).click()
  const classrooms = page.locator('#classrooms-panel')
  await expect(classrooms.getByText(/2[2-4] results · Page 1 of 2/)).toBeVisible()
  await classrooms.getByRole('button', { name: 'Next' }).click()
  await expect(classrooms.getByText(/2[2-4] results · Page 2 of 2/)).toBeVisible()
  await expect(classrooms.getByText('E2E-SCALE-021', { exact: true })).toBeVisible()
  await classrooms.getByRole('button', { name: 'Previous' }).click()
  await expect(classrooms.getByText(/2[2-4] results · Page 1 of 2/)).toBeVisible()
  await classrooms.getByRole('button', { name: 'Next' }).click()
  await page.getByPlaceholder('Search records…').fill('E2E-SCALE-021')
  await expect(classrooms.getByText('1 result · Page 1 of 1')).toBeVisible()

  await page.getByRole('tab', { name: /Cameras/ }).click()
  const cameras = page.locator('#cameras-panel')
  await expect(cameras.getByText(/2[2-3] results · Page 1 of 2/)).toBeVisible()
  await cameras.getByRole('button', { name: 'Next' }).click()
  await expect(cameras.getByText(/2[2-3] results · Page 2 of 2/)).toBeVisible()
  await expect(cameras.getByText('E2E Scale Camera 021', { exact: true })).toBeVisible()
  await cameras.getByRole('button', { name: 'Previous' }).click()
  await expect(cameras.getByText(/2[2-3] results · Page 1 of 2/)).toBeVisible()
})

test('teacher presentation, analytics, and report lists navigate to page two', async ({ page }) => {
  await login(page, accounts.teacher)

  await page.getByRole('link', { name: 'Live Session' }).click()
  const subjectSelector = page.getByRole('region', { name: 'Subject and classroom' })
  await expect(subjectSelector.getByText(/2[2-3] results · Page 1 of 2/)).toBeVisible()
  await subjectSelector.getByRole('button', { name: 'Next' }).click()
  await expect(subjectSelector.getByText(/2[2-3] results · Page 2 of 2/)).toBeVisible()
  await expect(subjectSelector.getByRole('option', { name: /E2E-SUBJECT-021/ })).toHaveCount(1)
  await subjectSelector.getByRole('button', { name: 'Previous' }).click()
  await expect(subjectSelector.getByText(/2[2-3] results · Page 1 of 2/)).toBeVisible()

  const presentations = page.getByRole('region', { name: 'Presentation Library' })
  await expect(presentations.getByText(/2[1-2] results · Page 1 of 2/)).toBeVisible()
  await presentations.getByRole('button', { name: 'Next' }).click()
  await expect(presentations.getByText(/2[1-2] results · Page 2 of 2/)).toBeVisible()
  await expect(presentations.getByText('E2E Scale Presentation 001', { exact: true })).toBeVisible()
  await presentations.getByRole('button', { name: 'Previous' }).click()
  await expect(presentations.getByText(/2[1-2] results · Page 1 of 2/)).toBeVisible()

  await page.getByRole('tab', { name: 'Class history' }).click()
  const recentSessions = page.locator('#history-panel')
  await expect(recentSessions.getByText(/2[1-2] results · Page 1 of 5/)).toBeVisible()
  await recentSessions.getByRole('button', { name: 'Next' }).click()
  await expect(recentSessions.getByText(/2[1-2] results · Page 2 of 5/)).toBeVisible()
  await recentSessions.getByRole('button', { name: 'Previous' }).click()
  await expect(recentSessions.getByText(/2[1-2] results · Page 1 of 5/)).toBeVisible()

  await page.getByRole('link', { name: 'Analytics', exact: true }).click()
  const analyticsPagination = page.locator('.analytics-pagination')
  await expect(page.getByText(/2[1-2] results · Page 1 of 2/)).toBeVisible()
  await analyticsPagination.getByRole('button', { name: 'Next' }).click()
  await expect(page.getByText(/2[1-2] results · Page 2 of 2/)).toBeVisible()
  await analyticsPagination.getByRole('button', { name: 'Previous' }).click()
  await expect(page.getByText(/2[1-2] results · Page 1 of 2/)).toBeVisible()

  await page.getByRole('link', { name: 'Reports' }).click()
  await expect(page.getByText(/2[1-2] results · Page 1 of 2/)).toHaveCount(2)
  await page.getByRole('button', { name: 'Next' }).last().click()
  await expect(page.getByText(/2[1-2] results · Page 2 of 2/)).toBeVisible()
  await page.getByRole('button', { name: 'Previous' }).last().click()
  await expect(page.getByText(/2[1-2] results · Page 1 of 2/)).toHaveCount(2)
})

test('configuration pickers search beyond the visible table page', async ({ page }) => {
  await login(page, accounts.organizationAdmin)
  await page.getByRole('link', { name: 'Classes', exact: true }).click()
  await page.getByRole('button', { name: 'Add Subject' }).click()

  await page.getByLabel('Search subject classrooms').fill('E2E-SCALE-021')
  const classroomPicker = page.getByLabel('Subject classroom', { exact: true })
  const classroomOption = classroomPicker.getByRole('option', { name: /E2E-SCALE-021/ })
  await expect(classroomOption).toHaveCount(1)
  await classroomPicker.selectOption(await classroomOption.getAttribute('value'))

  await page.getByLabel('Search subject teachers').fill('e2e.scale.teacher.021')
  const teacherPicker = page.getByLabel('Subject teacher', { exact: true })
  await expect(teacherPicker.getByRole('option', { name: 'Scale Teacher 021' })).toHaveCount(1)
  await teacherPicker.selectOption({ label: 'Scale Teacher 021' })
  await expect(classroomPicker).toHaveValue(/\d+/)
  await expect(teacherPicker).toHaveValue(/\d+/)
})

test('system administrator organization picker uses server search', async ({ page }) => {
  await login(page, accounts.systemAdmin)
  await page.getByRole('link', { name: 'Organization Admins', exact: true }).click()
  await page.getByRole('button', { name: 'Add Organization Admin', exact: true }).click()

  await page.getByLabel('Search organizations').fill('E2E-SCHOOL')
  await expect(page.getByLabel('Organization', { exact: true }).getByRole('option', {
    name: 'E2E Test School',
  })).toHaveCount(1)
})
