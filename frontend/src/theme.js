import { ref } from 'vue'

const STORAGE_KEY = 'matflow-theme'
const savedTheme = localStorage.getItem(STORAGE_KEY)
const initialTheme = savedTheme === 'dark' || savedTheme === 'light'
  ? savedTheme
  : (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')

const theme = ref(initialTheme)

function applyTheme(value = theme.value) {
  document.documentElement.dataset.theme = value
  document.documentElement.style.colorScheme = value
}

function setTheme(value) {
  theme.value = value === 'dark' ? 'dark' : 'light'
  localStorage.setItem(STORAGE_KEY, theme.value)
  applyTheme()
}

function toggleTheme() {
  setTheme(theme.value === 'dark' ? 'light' : 'dark')
}

applyTheme()

export function useTheme() {
  return { theme, setTheme, toggleTheme, applyTheme }
}
