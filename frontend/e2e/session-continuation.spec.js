import { accounts, createMinimalPdf, expect, login, test } from './support.js'

async function endClass(page, action) {
  await page.getByRole('button', { name: 'End Class', exact: true }).click()
  if (action === 'save') {
    await page.getByRole('dialog', { name: 'End this class?' }).getByRole('button', { name: 'Save & Continue Later' }).click()
  } else {
    await page.getByRole('dialog', { name: 'End this class?' }).getByRole('button', { name: 'Finish Lesson', exact: true }).click()
    await page.getByRole('dialog', { name: 'Finish this lesson?' }).getByRole('button', { name: 'Finish Lesson', exact: true }).click()
  }
}

async function postJson(page, url, data) {
  const cookie = (await page.context().cookies()).find(item => item.name === 'csrftoken')
  const response = await page.request.post(url, { data, headers: { 'X-CSRFToken': cookie.value } })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

test('saved lessons restore slides through refresh, cancellation, another tab, and a lost save response', async ({ page }, testInfo) => {
  test.setTimeout(120_000)
  const pdf = testInfo.outputPath('continuation.pdf')
  await createMinimalPdf(pdf, 3)
  await login(page, accounts.teacher)
  await page.getByRole('link', { name: 'Live Session' }).click()
  await page.getByLabel('Title', { exact: true }).fill('Continuation Browser Lesson')
  await page.getByLabel('File', { exact: true }).setInputFiles(pdf)
  await page.getByRole('button', { name: 'Upload Presentation', exact: true }).click()
  await expect(page.getByText('3 generated slides')).toBeVisible()
  const details = page.getByRole('region', { name: 'Session Details' })
  const subject = details.locator('select').nth(0)
  await subject.selectOption(await subject.locator('option').filter({ hasText: 'E2E-IT101' }).getAttribute('value'))
  await page.getByRole('button', { name: 'Clear', exact: true }).click()
  await page.getByRole('button', { name: 'Prepare Session', exact: true }).click()
  await page.getByRole('button', { name: 'Start Session', exact: true }).click()
  await expect(page.getByRole('button', { name: 'End Class', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  await expect(page.getByText('Slide 2 of 3', { exact: true })).toBeVisible()
  const endButton = page.getByRole('button', { name: 'End Class', exact: true })
  await endButton.click()
  const dialog = page.getByRole('dialog', { name: 'End this class?' })
  await expect(dialog.getByRole('button', { name: 'Save & Continue Later' })).toBeFocused()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByText('Slide 2 of 3', { exact: true })).toBeVisible()
  await dialog.getByRole('button', { name: 'Keep Teaching' }).click()
  await expect(endButton).toBeFocused()
  await endButton.click()
  await page.screenshot({ path: testInfo.outputPath('end-class-light.png') })
  await dialog.getByRole('button', { name: 'Save & Continue Later' }).click()
  const saved = page.getByRole('region', { name: 'Saved for Later' })
  const card = saved.getByRole('article', { name: 'Continuation Browser Lesson' })
  await expect(card.getByText('Slide 2 of 3', { exact: true })).toBeVisible()
  await page.reload()
  await expect(card.getByText('Slide 2 of 3', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('saved-lessons-light.png'), fullPage: true })
  await card.getByRole('button', { name: 'Continue Lesson', exact: true }).click()
  await page.getByRole('button', { name: 'Prepare Continuation', exact: true }).click()
  await expect(page.getByText('Slide 2 of 3', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('Slide 2 of 3', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Change setup', exact: true }).click()
  await page.getByRole('dialog', { name: 'Cancel session preparation?' }).getByRole('button', { name: 'Cancel preparation' }).click()
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: 'Continue Lesson', exact: true }).click()
  await page.getByRole('button', { name: 'Prepare Continuation', exact: true }).click()

  const other = await page.context().newPage()
  await other.goto('/session')
  await expect(other.getByText('Slide 2 of 3', { exact: true })).toBeVisible()
  await other.getByRole('button', { name: 'Start Session', exact: true }).click()
  await expect(other.getByRole('button', { name: 'End Class', exact: true })).toBeVisible()
  await expect(endButton).toBeVisible()
  await other.getByRole('button', { name: 'Next', exact: true }).click()
  await expect(page.getByText('Slide 3 of 3', { exact: true })).toBeVisible()
  await page.route('**/api/auth/sessions/*/end/', async route => {
    await route.fetch()
    await route.abort('failed')
  })
  await endClass(page, 'save')
  await expect(card.getByText('Slide 3 of 3', { exact: true })).toBeVisible()
  await expect(other.getByRole('region', { name: 'Saved for Later' })).toBeVisible()
  await other.close()
  await page.unroute('**/api/auth/sessions/*/end/')
  await card.getByRole('button', { name: 'Finish Lesson', exact: true }).click()
  await page.getByRole('dialog', { name: 'Finish this lesson?' }).getByRole('button', { name: 'Finish Lesson', exact: true }).click()
  await expect(card).toHaveCount(0)
  await page.getByRole('tab', { name: 'Class history' }).click()
  const recent = page.locator('#history-panel')
  await recent.getByRole('button', { name: 'Lesson history', exact: true }).first().click()
  const history = page.locator('#history-panel')
  await expect(history.getByRole('link', { name: 'View analytics' })).toHaveCount(2)
  await expect(history.getByText('Class saved', { exact: true })).toHaveCount(2)
  await expect(history.getByText('Lesson Completed', { exact: false })).toHaveCount(2)
  await history.getByRole('link', { name: 'View analytics' }).first().click()
  await expect(page.getByText(/Class saved · Class #/)).toBeVisible()
  await page.getByRole('link', { name: 'Lesson history', exact: true }).click()
  await expect(history.getByRole('link', { name: 'View analytics' })).toHaveCount(2)
  await page.getByRole('link', { name: 'Reports', exact: true }).click()
  await expect(page.getByLabel('Closed class meeting')).toContainText('Class saved')
})

test('analytics opens an exact linked meeting outside the current options page', async ({ page }) => {
  await login(page, accounts.teacher)
  const response = await (await page.request.get('/api/auth/analytics/sessions/')).json()
  const session = response.results[0]
  await page.route('**/api/auth/analytics/sessions/?*', async route => {
    const result = await route.fetch()
    const data = await result.json()
    await route.fulfill({ json: { ...data, results: data.results.filter(item => item.id !== session.id) } })
  })
  await page.goto(`/analytics?session=${session.id}`)
  await expect(page.getByLabel('Session:', { exact: true })).toHaveValue(String(session.id))
  await expect(page.getByText(`Class saved · Class #${session.id}`, { exact: true })).toBeVisible()
  await page.goto('/analytics?session=2147483647')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByText('Session Duration', { exact: true })).toHaveCount(0)
})

test('unconfirmed actions block competing controls and recover on a mobile dark layout', async ({ page }, testInfo) => {
  await login(page, accounts.teacher)
  const subjects = await (await page.request.get('/api/auth/session-subjects/')).json()
  const presentations = await (await page.request.get('/api/auth/presentations/')).json()
  const presentation = presentations.results.find(item => item.title === 'Continuation Browser Lesson')
  const session = await postJson(page, '/api/auth/sessions/', { subject: subjects.results[0].id, presentation: presentation.id, cameras: [] })
  await page.goto('/session')
  await expect(page.getByRole('button', { name: 'End Class', exact: true })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.evaluate(() => document.documentElement.classList.add('dark'))
  await page.route('**/api/auth/sessions/*/end/', route => route.fulfill({ status: 503, json: { detail: 'Unavailable' } }))
  const detailUrl = `**/api/auth/sessions/${session.id}/`
  await page.route(detailUrl, route => route.abort('failed'))
  await endClass(page, 'save')
  const dialog = page.getByRole('dialog', { name: 'End this class?' })
  await expect(dialog.getByRole('button', { name: 'Check status', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Keep Teaching' })).toHaveCount(0)
  await page.screenshot({ path: testInfo.outputPath('recovery-mobile-dark.png') })
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.unroute(detailUrl)
  await page.unroute('**/api/auth/sessions/*/end/')
  await dialog.getByRole('button', { name: 'Check status', exact: true }).click()
  await expect(dialog.getByRole('button', { name: 'Keep Teaching' })).toBeEnabled()
  await dialog.getByRole('button', { name: 'Keep Teaching' }).click()
  await page.context().clearCookies()
  await page.getByRole('link', { name: 'Sign in again', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()
  await login(page, accounts.teacher)
  await page.goto('/session')
  await expect(page.getByText('Slide 1 of 3', { exact: true })).toBeVisible()
  await endClass(page, 'finish')
  await expect(page).toHaveURL(/\/analytics\?session=\d+$/)
})

test('prepared camera stays Online when teaching starts and still reports a later failure', async ({ page }, testInfo) => {
  const pdf = testInfo.outputPath('camera-handoff.pdf')
  await createMinimalPdf(pdf)
  await login(page, accounts.teacher)
  await page.getByRole('link', { name: 'Live Session', exact: true }).click()
  await page.getByLabel('Title', { exact: true }).fill('Camera Handoff Lesson')
  await page.getByLabel('File', { exact: true }).setInputFiles(pdf)
  await page.getByRole('button', { name: 'Upload Presentation', exact: true }).click()
  const uploaded = page.getByRole('region', { name: 'Presentation Library' }).locator('div.rounded-lg').filter({ hasText: 'Camera Handoff Lesson' }).first()
  await expect(uploaded.getByText('1 generated slides', { exact: true })).toBeVisible()
  await page.route('**/api/auth/session-cameras/availability/', async route => {
    const { camera_ids: ids } = route.request().postDataJSON()
    await route.fulfill({ json: { cameras: ids.map(id => ({ camera_id: id, state: 'available' })) } })
  })
  const details = page.getByRole('region', { name: 'Session Details' })
  const subjects = details.locator('select').first()
  await subjects.selectOption(await subjects.locator('option').filter({ hasText: 'E2E-IT101' }).getAttribute('value'))
  const preparedResponse = page.waitForResponse(response => response.url().endsWith('/sessions/prepare/') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Prepare Session', exact: true }).click()
  const session = await (await preparedResponse).json()
  const heartbeat = async state => {
    const response = await page.request.post('/api/auth/pipeline/cameras/heartbeat/', {
      headers: { 'X-Pipeline-Key': 'e2e-pipeline-key' },
      data: {
        session_id: session.id, camera_id: session.cameras[0].id, state,
        source_type: 'simulated', pipeline_version: 'e2e-handoff',
        reason: { online: 'processing', offline: 'retry_exhausted' }[state] || '',
        analysis_rate: 1, yolo_candidates: 0, valid_faces: 0,
        confirmed_students: 0, unclassified_students: 0,
        counts: { engaged: 0, attentive: 0, confused: 0, bored: 0, disengaged: 0 },
      },
    })
    expect(response.ok()).toBeTruthy()
  }
  await heartbeat('starting')
  const health = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Camera & Worker Health', exact: true }) })
  await expect(health.getByText('Preparing', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start Session', exact: true })).toBeDisabled()
  await heartbeat('online')
  await expect(health.getByText('Online', { exact: true })).toBeVisible()

  let releaseHealth
  const heldHealth = new Promise(resolve => { releaseHealth = resolve })
  const healthUrl = `**/api/auth/sessions/${session.id}/camera-health/`
  await page.route(healthUrl, async route => { await heldHealth; await route.continue() })
  try {
    await page.getByRole('button', { name: 'Start Session', exact: true }).click()
    await expect(page.getByRole('button', { name: 'End Class', exact: true })).toBeVisible()
    await expect(health.getByText('Online', { exact: true })).toBeVisible()
    await expect(health.getByText('Live status', { exact: true })).toBeVisible()
    await expect(health.getByText('Stopped', { exact: true })).toHaveCount(0)
    await heartbeat('offline')
  } finally {
    releaseHealth()
    await page.unroute(healthUrl)
  }
  await expect(health.getByText('Offline', { exact: true })).toBeVisible()
  await endClass(page, 'finish')
  await expect(page).toHaveURL(/\/analytics\?session=\d+$/)
})
