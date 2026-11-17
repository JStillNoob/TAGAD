import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const styles = await readFile(new URL('../src/assets/main.css', import.meta.url), 'utf8')

function channel(value) {
  const normalized = value / 255
  return normalized <= 0.04045
    ? normalized / 12.92
    : ((normalized + 0.055) / 1.055) ** 2.4
}

function luminance(hex) {
  const channels = hex.match(/[\da-f]{2}/gi).map(value => channel(Number.parseInt(value, 16)))
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrast(first, second) {
  const values = [luminance(first), luminance(second)].sort((a, b) => b - a)
  return (values[0] + 0.05) / (values[1] + 0.05)
}

test('subtle text tokens meet normal-text contrast on application surfaces', () => {
  assert.ok(contrast('586079', 'FFFFFF') >= 4.5)
  assert.ok(contrast('586079', 'ECEEF0') >= 4.5)
  assert.ok(contrast('A8B3C5', '111827') >= 4.5)
  assert.ok(contrast('A8B3C5', '0F172A') >= 4.5)
  assert.match(styles, /--text-subtle: #586079;/)
  assert.match(styles, /--text-subtle: #A8B3C5;/)
})

test('legacy subtle text and placeholders use the semantic contrast token', () => {
  assert.match(styles, /\.text-gray-400 \{ color: var\(--text-subtle\); \}/)
  assert.match(styles, /input::placeholder,[\s\S]*color: var\(--text-subtle\); opacity: 1;/)
  assert.match(styles, /\.platform-search-field > input::placeholder \{ color: var\(--text-subtle\); opacity: 1; \}/)
})

test('flat brand and action surfaces retain readable white text', () => {
  assert.ok(contrast('FFFFFF', '1A2A66') >= 4.5)
  assert.ok(contrast('FFFFFF', '506BC9') >= 4.5)
  assert.ok(contrast('FFFFFF', '3E53A0') >= 4.5)
  assert.match(styles, /\.login-brand-panel \{[^\n]*background: #1A2A66;/)
  assert.match(styles, /\.login-content \.login-submit \{[^\n]*background: var\(--primary-action\);/)
})
