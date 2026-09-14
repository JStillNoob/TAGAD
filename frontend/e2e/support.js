import { writeFile } from 'node:fs/promises'
import { expect, test as base } from '@playwright/test'


export const password = 'BrowserTest!2026'
export const accounts = {
  systemAdmin: 'e2e.system',
  organizationAdmin: 'e2e.admin',
  teacher: 'e2e.teacher',
}

function safeDiagnostic(value) {
  return value
    .replace(/\/reset-password\/[^/\s]+\/[^/\s]+/g, '/reset-password/[redacted]')
    .replace(/([?&](?:token|key)=)[^&\s]+/gi, '$1[redacted]')
}

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const diagnostics = []
    page.on('pageerror', (error) => diagnostics.push(`page: ${error.message}`))
    page.on('response', (response) => {
      if (response.status() >= 500) {
        diagnostics.push(`response: ${response.status()} ${response.request().method()} ${response.url()}`)
      }
    })
    page.on('requestfailed', (request) => {
      const reason = request.failure()?.errorText || 'unknown failure'
      if (!reason.includes('ERR_ABORTED')) {
        diagnostics.push(`request: ${request.method()} ${request.url()} (${reason})`)
      }
    })

    await use(page)

    if (diagnostics.length && testInfo.status !== testInfo.expectedStatus) {
      await testInfo.attach('browser-diagnostics.txt', {
        body: Buffer.from(safeDiagnostic(diagnostics.join('\n'))),
        contentType: 'text/plain',
      })
    }
  },
})

export { expect }

export async function login(page, identity) {
  await page.goto('/')
  await page.getByLabel('Email or Username').fill(identity)
  await page.getByLabel('Password').fill(password)
  await page.locator('form').getByRole('button', { name: 'Start Session' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

export async function logout(page) {
  await page.getByLabel('Open account menu').click()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/$/)
}

export async function createMinimalPdf(filePath) {
  const stream = 'BT\n/F1 24 Tf\n72 720 Td\n(TAGAD browser test) Tj\nET\n'
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}endstream`,
  ]

  let content = '%PDF-1.4\n'
  const offsets = [0]
  for (const [index, object] of objects.entries()) {
    offsets.push(Buffer.byteLength(content))
    content += `${index + 1} 0 obj\n${object}\nendobj\n`
  }
  const xrefOffset = Buffer.byteLength(content)
  content += `xref\n0 ${objects.length + 1}\n`
  content += '0000000000 65535 f \n'
  content += offsets.slice(1).map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  content += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`
  await writeFile(filePath, content, 'ascii')
}
