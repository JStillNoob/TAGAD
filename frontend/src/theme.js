import { readonly, ref } from 'vue'

export const THEME_STORAGE_KEY = 'tagad-theme'

const themeState = ref('light')
let systemPreference = null

export const currentTheme = readonly(themeState)

export function resolveInitialTheme(storedTheme, systemPrefersDark) {
  if (storedTheme === 'light' || storedTheme === 'dark') return storedTheme
  return systemPrefersDark ? 'dark' : 'light'
}

function applyTheme(theme) {
  themeState.value = theme
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document.documentElement.style.colorScheme = theme
}

function handleSystemTheme(event) {
  if (!localStorage.getItem(THEME_STORAGE_KEY)) {
    applyTheme(event.matches ? 'dark' : 'light')
  }
}

export function initializeTheme() {
  systemPreference = window.matchMedia('(prefers-color-scheme: dark)')
  applyTheme(resolveInitialTheme(
    localStorage.getItem(THEME_STORAGE_KEY),
    systemPreference.matches,
  ))
  systemPreference.addEventListener('change', handleSystemTheme)
}

export function toggleTheme() {
  const nextTheme = themeState.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
  applyTheme(nextTheme)
}
