import { computed, ref } from 'vue'

export type AppTheme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'app_theme'

function readStoredTheme(): AppTheme | null {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    return saved === 'light' || saved === 'dark' ? saved : null
  } catch {
    return null
  }
}

function systemPrefersDark() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

const theme = ref<AppTheme>(readStoredTheme() ?? (systemPrefersDark() ? 'dark' : 'light'))

function applyTheme(value: AppTheme) {
  document.documentElement.classList.toggle('dark', value === 'dark')
}

applyTheme(theme.value)

// Follow the OS setting until the user picks a theme explicitly.
window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
  if (readStoredTheme()) return
  theme.value = event.matches ? 'dark' : 'light'
  applyTheme(theme.value)
})

export function useTheme() {
  const isDark = computed(() => theme.value === 'dark')

  function setTheme(value: AppTheme) {
    theme.value = value
    applyTheme(value)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, value)
    } catch {
      // storage can be unavailable (private mode); the theme still applies for this session
    }
  }

  function toggleTheme() {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  return { theme, isDark, setTheme, toggleTheme }
}
