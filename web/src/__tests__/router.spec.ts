import { describe, it, expect } from 'vitest'
import { flushPromises } from '@vue/test-utils'

import App from '../App.vue'
import { mountWithPlugins } from '@/test-utils/mount'

describe('routes', () => {
  it('renders the home page at /', async () => {
    const { wrapper, router } = await mountWithPlugins(App, { route: '/' })
    const main = wrapper.find('main')

    expect(router.currentRoute.value.name).toBe('home')
    expect(main.find('h1').text()).toBe('Problema de acceso a la vivienda en España')
    expect(main.text()).toContain('Qué investiga')
    expect(main.text()).toContain('Precios de compra y alquiler')
    expect(main.text()).toContain('Qué no ofrece')
    expect(main.text()).toContain('Asesoramiento jurídico o financiero personalizado')
    expect(main.text()).toContain('Tasaciones de inmuebles')
    expect(main.text()).toContain('Recomendaciones de inversión')
    expect(main.text()).toContain('Previsiones')
  })

  it('renders the not-found page for unknown paths and keeps the path', async () => {
    const { wrapper, router } = await mountWithPlugins(App, { route: '/no-existe' })
    await flushPromises()
    const main = wrapper.find('main')

    expect(router.currentRoute.value.name).toBe('notFound')
    expect(router.currentRoute.value.fullPath).toBe('/no-existe')
    expect(main.text()).toContain('Página no encontrada')
    expect(main.find('a').attributes('href')).toBe('/')
  })

  it('returns to home on back navigation', async () => {
    const { router } = await mountWithPlugins(App, { route: '/' })
    await router.push('/no-existe')
    expect(router.currentRoute.value.name).toBe('notFound')

    const navigated = new Promise<void>((resolve) => router.afterEach(() => resolve()))
    router.back()
    await navigated

    expect(router.currentRoute.value.name).toBe('home')
    expect(router.currentRoute.value.fullPath).toBe('/')
  })
})
