import { ref, watch } from 'vue'

const THEME_KEY = 'app-theme'
const theme = ref(localStorage.getItem(THEME_KEY) || 'dark')

export function useTheme() {
  const toggleTheme = () => {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  const setTheme = (t) => {
    theme.value = t
  }

  watch(theme, (val) => {
    document.documentElement.setAttribute('data-theme', val)
    localStorage.setItem(THEME_KEY, val)
  }, { immediate: true })

  return { theme, toggleTheme, setTheme }
}
