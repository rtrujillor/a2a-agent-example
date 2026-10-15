import { readFileSync } from 'node:fs'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'

import { THEME_STORAGE_KEY, useThemeStore } from '@/stores/theme'

// A controllable `prefers-color-scheme: dark` media query.
function stubSystemPreference(prefersDark: boolean) {
  const listeners = new Set<(event: { matches: boolean }) => void>()
  const query = {
    matches: prefersDark,
    media: '(prefers-color-scheme: dark)',
    addEventListener: (_: string, listener: (event: { matches: boolean }) => void) =>
      listeners.add(listener),
    removeEventListener: (_: string, listener: (event: { matches: boolean }) => void) =>
      listeners.delete(listener),
  }
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => query),
  )
  return {
    change(next: boolean) {
      query.matches = next
      listeners.forEach((listener) => listener({ matches: next }))
    },
  }
}

const html = document.documentElement

// Stores outlive their test unless disposed; a live one would still react to
// storage and system changes made by later tests.
const created: ReturnType<typeof useThemeStore>[] = []
function themeStore() {
  const store = useThemeStore()
  created.push(store)
  return store
}
const isDarkClass = () => html.classList.contains('dark')

describe('theme store', () => {
  beforeEach(() => {
    localStorage.clear()
    html.className = ''
    setActivePinia(createPinia())
  })
  afterEach(() => {
    created.splice(0).forEach((store) => store.$dispose())
    vi.unstubAllGlobals()
  })

  it('defaults to system and follows a dark system preference', async () => {
    stubSystemPreference(true)
    const theme = themeStore()
    await nextTick()

    expect(theme.mode).toBe('system')
    expect(isDarkClass()).toBe(true)
  })

  it('lets an explicit choice override the system', async () => {
    stubSystemPreference(true)
    const theme = themeStore()
    theme.setMode('light')
    await nextTick()

    expect(theme.mode).toBe('light')
    expect(isDarkClass()).toBe(false)
  })

  it('switches live when the system changes while on system', async () => {
    const system = stubSystemPreference(false)
    themeStore()
    await nextTick()
    expect(isDarkClass()).toBe(false)

    system.change(true)
    await nextTick()
    expect(isDarkClass()).toBe(true)
  })

  it('ignores system changes while on an explicit choice', async () => {
    const system = stubSystemPreference(true)
    const theme = themeStore()
    theme.setMode('dark')
    await nextTick()

    system.change(false)
    await nextTick()
    expect(isDarkClass()).toBe(true)
  })

  it('remembers the choice across reloads', async () => {
    stubSystemPreference(false)
    themeStore().setMode('dark')
    await nextTick()
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')

    setActivePinia(createPinia())
    html.className = ''
    const reloaded = themeStore()
    await nextTick()
    expect(reloaded.mode).toBe('dark')
    expect(isDarkClass()).toBe(true)
  })

  it('falls back to system on an unrecognized stored value', async () => {
    stubSystemPreference(true)
    localStorage.setItem(THEME_STORAGE_KEY, 'sepia')
    const theme = themeStore()
    await nextTick()

    expect(theme.mode).toBe('system')
    expect(isDarkClass()).toBe(true)
  })

  it('falls back to system when storage is blocked', async () => {
    stubSystemPreference(true)
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('blocked', 'SecurityError')
    })
    const theme = themeStore()
    await nextTick()

    expect(theme.mode).toBe('system')
    expect(isDarkClass()).toBe(true)
    vi.restoreAllMocks()
  })
})

describe('pre-paint theme script', () => {
  const page = readFileSync('index.html', 'utf8')
  const script = page.slice(page.indexOf('<script>'), page.indexOf('</script>'))

  it('runs in the head, before the app', () => {
    expect(page.indexOf('<script>')).toBeLessThan(page.indexOf('</head>'))
  })

  it("uses the store's storage key and values", () => {
    expect(script).toContain(`getItem('${THEME_STORAGE_KEY}')`)
    expect(script).toContain("'dark'")
    expect(script).toContain("'light'")
    expect(script).toContain('prefers-color-scheme: dark')
  })
})
