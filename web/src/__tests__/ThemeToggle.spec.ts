import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'

import ThemeToggle from '@/components/ThemeToggle.vue'
import { useThemeStore } from '@/stores/theme'
import { mountWithPlugins } from '@/test-utils/mount'

let wrapper: VueWrapper

function items() {
  return Array.from(document.body.querySelectorAll<HTMLElement>('[role="menuitemradio"]'))
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal(
      'matchMedia',
      vi.fn(() => ({ matches: false, addEventListener() {}, removeEventListener() {} })),
    )
    // jsdom has no ResizeObserver; Reka UI measures the menu with it.
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    )
  })
  afterEach(() => {
    wrapper?.unmount()
    vi.unstubAllGlobals()
  })

  it('has a Spanish accessible name', async () => {
    ;({ wrapper } = await mountWithPlugins(ThemeToggle, { attachTo: document.body }))
    expect(wrapper.find('button').attributes('aria-label')).toBe('Tema')
  })

  it('lets a keyboard user choose the dark theme', async () => {
    ;({ wrapper } = await mountWithPlugins(ThemeToggle, { attachTo: document.body }))
    const trigger = wrapper.find('button')
    trigger.element.focus()
    await trigger.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(items().map((item) => item.textContent?.trim())).toEqual(['Claro', 'Oscuro', 'Sistema'])
    const system = items().find((item) => item.textContent?.includes('Sistema'))!
    expect(system.getAttribute('aria-checked')).toBe('true')

    const dark = items().find((item) => item.textContent?.includes('Oscuro'))!
    dark.focus()
    dark.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    await flushPromises()

    expect(useThemeStore().mode).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    await trigger.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    const reopened = items().find((item) => item.textContent?.includes('Oscuro'))!
    expect(reopened.getAttribute('aria-checked')).toBe('true')
  })
})
