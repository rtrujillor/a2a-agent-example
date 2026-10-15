import { defineStore } from 'pinia'
import { computed } from 'vue'
import { useColorMode, type StorageLike } from '@vueuse/core'

export type ThemeMode = 'light' | 'dark' | 'system'

// Shared with the pre-paint script in index.html; keep both in sync.
// Stored values: 'light', 'dark', or 'auto' (vueuse's name for system).
export const THEME_STORAGE_KEY = 'theme'

// The only state the client keeps in the browser. Storage may be blocked
// (private modes, disabled cookies): then the choice lasts for the session.
function browserStorage(): StorageLike {
  try {
    const storage = window.localStorage
    storage.getItem(THEME_STORAGE_KEY)
    return storage
  } catch {
    return { getItem: () => null, setItem: () => {}, removeItem: () => {} }
  }
}

export const useThemeStore = defineStore('theme', () => {
  // Toggles the `dark` class on <html> and follows the system live on 'auto'.
  const colorMode = useColorMode({
    storageKey: THEME_STORAGE_KEY,
    storage: browserStorage(),
    initialValue: 'auto',
  })

  const stored = colorMode.store
  if (stored.value !== 'light' && stored.value !== 'dark' && stored.value !== 'auto') {
    stored.value = 'auto'
  }

  const mode = computed<ThemeMode>(() =>
    stored.value === 'light' || stored.value === 'dark' ? stored.value : 'system',
  )
  const isDark = computed(() => colorMode.state.value === 'dark')

  function setMode(next: ThemeMode) {
    stored.value = next === 'system' ? 'auto' : next
  }

  return { mode, isDark, setMode }
})
