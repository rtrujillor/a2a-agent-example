import { describe, it, expect } from 'vitest'
import { getActivePinia } from 'pinia'

import App from '../App.vue'
import { mountWithPlugins } from '@/test-utils/mount'

describe('App', () => {
  it('shows the application name in the header', async () => {
    const { wrapper } = await mountWithPlugins(App)
    expect(wrapper.find('header').text()).toContain('Acceso a la vivienda en España')
  })

  it('links the header application name to the home page', async () => {
    const { wrapper, router } = await mountWithPlugins(App, { route: '/no-existe' })
    const link = wrapper.find('header a')
    expect(link.attributes('href')).toBe('/')

    const navigated = new Promise<void>((resolve) => router.afterEach(() => resolve()))
    await link.trigger('click')
    await navigated
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('registers an active Pinia instance', async () => {
    const { pinia } = await mountWithPlugins(App)
    expect(getActivePinia()).toBe(pinia)
  })
})
