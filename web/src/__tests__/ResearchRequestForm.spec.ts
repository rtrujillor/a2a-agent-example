import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'

import HomeView from '@/views/HomeView.vue'
import { AgentUnavailableError, a2aService } from '@/services/a2aClient'
import { mountWithPlugins } from '@/test-utils/mount'
import type { ResearchSubmission } from '@/types/research'

vi.mock('@/services/a2aClient', () => ({
  AgentUnavailableError: class AgentUnavailableError extends Error {},
  a2aService: { submitResearch: vi.fn<(text: string) => Promise<ResearchSubmission>>() },
}))

const submitResearch = vi.mocked(a2aService.submitResearch)

const accepted: ResearchSubmission = {
  first: { kind: 'task', taskId: 'task-1', contextId: 'ctx-1', state: 'TASK_STATE_SUBMITTED', text: '' },
  events: { next: vi.fn<ResearchSubmission['events']['next']>() },
  close: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
}

const CONNECTION_ERROR = 'No se pudo conectar con el agente. Inténtalo de nuevo más tarde.'

let wrapper: VueWrapper

async function mountHome() {
  ;({ wrapper } = await mountWithPlugins(HomeView))
  return {
    textarea: wrapper.find('textarea'),
    button: wrapper.find('button[type="submit"]'),
    status: wrapper.find('[aria-live="polite"]'),
  }
}

describe('ResearchRequestForm', () => {
  beforeEach(() => submitResearch.mockReset())
  afterEach(() => wrapper?.unmount())

  it('comes before the scope details, with a labeled field and a named submit button', async () => {
    const { textarea, button } = await mountHome()
    const html = wrapper.html()

    expect(html.indexOf('<h1')).toBeLessThan(html.indexOf('<form'))
    expect(html.indexOf('</form>')).toBeLessThan(html.indexOf('Qué no ofrece'))
    const label = wrapper.find(`label[for="${textarea.attributes('id')}"]`)
    expect(label.text()).toBe('Pregunta sobre el acceso a la vivienda en España')
    expect(button.attributes('aria-label')).toBe('Enviar')
  })

  it('grows with the question up to a maximum height', async () => {
    const { textarea } = await mountHome()
    expect(textarea.classes()).toEqual(expect.arrayContaining(['field-sizing-content', 'max-h-64']))
  })

  it.each([
    ['MacIntel', '⌘', 'Comando'],
    ['Win32', 'Ctrl', 'Control'],
  ])('shows the submit shortcut next to the button on %s', async (platform, key, spoken) => {
    vi.stubGlobal('navigator', { ...navigator, platform })
    const { button } = await mountHome()
    const hint = wrapper.find('[data-testid="submit-shortcut"]')

    expect(hint.findAll('kbd').map((kbd) => kbd.text())).toEqual([key, '↵'])
    expect(hint.element.parentElement).toBe(button.element.parentElement)
    expect(wrapper.text()).toContain(`pulsa ${spoken} más Intro`)
    vi.unstubAllGlobals()
  })

  it('does not submit on Enter alone', async () => {
    const { textarea } = await mountHome()
    await textarea.setValue('Hola')
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(submitResearch).not.toHaveBeenCalled()
  })

  it.each([['ctrlKey'], ['metaKey']])('submits on Enter with %s', async (modifier) => {
    submitResearch.mockResolvedValue(accepted)
    const { textarea } = await mountHome()
    await textarea.setValue('Hola')
    await textarea.trigger('keydown', { key: 'Enter', [modifier]: true })
    expect(submitResearch).toHaveBeenCalledWith('Hola')
  })

  it.each([
    ['empty', '   ', 'Escribe una pregunta.'],
    ['too long', 'a'.repeat(2001), 'La pregunta no puede superar los 2000 caracteres.'],
  ])('shows the %s message and keeps the text', async (_label, text, message) => {
    const { textarea, button, status } = await mountHome()
    await textarea.setValue(text)
    await button.trigger('submit')
    await flushPromises()

    expect(status.text()).toBe(message)
    expect(status.classes()).toContain('text-destructive')
    expect(textarea.attributes('aria-invalid')).toBe('true')
    expect(textarea.attributes('aria-describedby')).toBe(status.attributes('id'))
    expect((textarea.element as HTMLTextAreaElement).value).toBe(text)
    expect(submitResearch).not.toHaveBeenCalled()
  })

  it('disables the busy button while sending, so a double click sends once', async () => {
    let resolve!: (value: ResearchSubmission) => void
    submitResearch.mockReturnValue(new Promise((r) => (resolve = r)))
    const { textarea, button } = await mountHome()
    await textarea.setValue('Hola')

    await wrapper.find('form').trigger('submit')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.attributes('aria-busy')).toBe('true')
    await wrapper.find('form').trigger('submit')

    resolve(accepted)
    await flushPromises()
    expect(submitResearch).toHaveBeenCalledOnce()
    expect(button.attributes('disabled')).toBeUndefined()
  })

  it('confirms an accepted request', async () => {
    submitResearch.mockResolvedValue(accepted)
    const { textarea, status } = await mountHome()
    await textarea.setValue('¿Cuántas viviendas turísticas hay en Barcelona?')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(status.text()).toBe('Solicitud enviada.')
    expect(status.classes()).not.toContain('text-destructive')
    expect((textarea.element as HTMLTextAreaElement).value).toBe(
      '¿Cuántas viviendas turísticas hay en Barcelona?',
    )
  })

  it('shows only the fixed connection message when the agent is unavailable', async () => {
    submitResearch.mockRejectedValueOnce(new AgentUnavailableError('TypeError: Failed to fetch'))
    const { textarea, button, status } = await mountHome()
    await textarea.setValue('Hola')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(status.text()).toBe(CONNECTION_ERROR)
    expect(status.classes()).toContain('text-destructive')
    expect(wrapper.text()).not.toContain('Failed to fetch')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('Hola')
    expect(button.attributes('disabled')).toBeUndefined()
  })

  it('announces the status politely without moving focus', async () => {
    submitResearch.mockResolvedValue(accepted)
    const host = document.body.appendChild(document.createElement('div'))
    ;({ wrapper } = await mountWithPlugins(HomeView, { attachTo: host }))
    const textarea = wrapper.find('textarea')
    ;(textarea.element as HTMLTextAreaElement).focus()
    await textarea.setValue('Hola')
    await textarea.trigger('keydown', { key: 'Enter', ctrlKey: true })
    await flushPromises()

    expect(wrapper.find('[aria-live="polite"]').text()).toBe('Solicitud enviada.')
    expect(document.activeElement).toBe(textarea.element)
  })
})
