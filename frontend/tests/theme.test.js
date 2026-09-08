import test from 'node:test'
import assert from 'node:assert/strict'

import {
  THEME_STORAGE_KEY,
  currentTheme,
  initializeTheme,
  resolveInitialTheme,
  toggleTheme,
} from '../src/theme.js'


test('stored preference overrides the system preference', () => {
  assert.equal(resolveInitialTheme('light', true), 'light')
  assert.equal(resolveInitialTheme('dark', false), 'dark')
})

test('system preference is used when no preference is stored', () => {
  assert.equal(resolveInitialTheme(null, true), 'dark')
  assert.equal(resolveInitialTheme(null, false), 'light')
})

test('initialization applies system theme and toggle stores the choice', () => {
  const stored = new Map()
  let darkClass = false
  globalThis.localStorage = {
    getItem: key => stored.get(key) || null,
    setItem: (key, value) => stored.set(key, value),
  }
  globalThis.document = {
    documentElement: {
      classList: { toggle: (_name, enabled) => { darkClass = enabled } },
      style: {},
    },
  }
  globalThis.window = {
    matchMedia: () => ({ matches: true, addEventListener: () => {} }),
  }

  initializeTheme()
  assert.equal(currentTheme.value, 'dark')
  assert.equal(darkClass, true)

  toggleTheme()
  assert.equal(currentTheme.value, 'light')
  assert.equal(darkClass, false)
  assert.equal(stored.get(THEME_STORAGE_KEY), 'light')
})
