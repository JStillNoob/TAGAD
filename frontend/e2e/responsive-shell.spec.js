import { accounts, expect, login, test } from './support.js'

test('authenticated navigation uses desktop, tablet, and phone shell states', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await login(page, accounts.teacher)

  const sidebar = page.locator('#app-navigation')
  const main = page.locator('.app-shell > div.flex-1')
  await expect(sidebar).toHaveClass(/app-sidebar-expanded/)
  expect((await main.boundingBox()).x).toBeGreaterThan(200)

  await page.setViewportSize({ width: 768, height: 1024 })
  await expect(sidebar).toHaveClass(/app-sidebar-collapsed/)
  await expect.poll(async () => (await main.boundingBox()).x).toBeGreaterThanOrEqual(70)
  await expect.poll(async () => (await main.boundingBox()).x).toBeLessThan(110)
  await expect(page.getByRole('button', { name: 'Expand sidebar' })).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(sidebar).toHaveAttribute('aria-hidden', 'true')
  await expect.poll(async () => (await main.boundingBox()).x).toBe(0)

  await page.getByRole('button', { name: 'Open navigation' }).click()
  await expect(sidebar).toHaveClass(/app-sidebar-expanded/)
  await expect(sidebar).toHaveAttribute('aria-modal', 'true')
  await expect(page.locator('.app-sidebar-backdrop')).toBeVisible()

  await page.keyboard.press('Escape')
  await expect(sidebar).toHaveAttribute('aria-hidden', 'true')
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused()
})

test('data pages stay within tablet and phone viewports', async ({ page }) => {
  await login(page, accounts.teacher)

  for (const viewport of [{ width: 768, height: 1024 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport)
    for (const path of ['/dashboard', '/analytics', '/reports', '/logs']) {
      await page.goto(path)
      await expect(page.locator('main')).toBeVisible()
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
    }

    await page.goto('/classes')
    await page.getByRole('tab', { name: /Classrooms/ }).click()
    await expect(page.locator('#classrooms-panel')).toBeVisible()
    await page.getByRole('tab', { name: /Cameras/ }).click()
    await expect(page.locator('#cameras-panel')).toBeVisible()
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  }
})

test('top navigation stays visible while page content scrolls', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await login(page, accounts.teacher)

  const topbar = page.locator('.app-topbar')
  await page.locator('main').evaluate((main) => {
    main.style.minHeight = '2000px'
  })
  await page.evaluate(() => window.scrollTo(0, 600))

  await expect.poll(async () => Math.round((await topbar.boundingBox()).y)).toBe(0)
  await expect(topbar).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await page.evaluate(() => window.scrollTo(0, 900))

  await expect.poll(async () => Math.round((await topbar.boundingBox()).y)).toBe(0)
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible()
})
