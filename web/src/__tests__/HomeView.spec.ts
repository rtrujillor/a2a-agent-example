import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'

import HomeView from '@/views/HomeView.vue'
import { a2aService } from '@/services/a2aClient'
import { mountWithPlugins } from '@/test-utils/mount'
import type { ResearchSubmission } from '@/types/research'

vi.mock('@/services/a2aClient', () => ({
  AgentUnavailableError: class AgentUnavailableError extends Error {},
  a2aService: { submitResearch: vi.fn<(text: string) => Promise<ResearchSubmission>>() },
}))

const submitResearch = vi.mocked(a2aService.submitResearch)

// Vitest stubs CSS imports, so the stylesheet is read from disk (root: web/).
const css = readFileSync('src/styles/main.css', 'utf8')

let wrapper: VueWrapper

describe('HomeView', () => {
  beforeEach(() => submitResearch.mockReset())
  afterEach(() => wrapper?.unmount())

  it('sets the title in the serif heading face', async () => {
    ;({ wrapper } = await mountWithPlugins(HomeView))
    expect(wrapper.find('h1').classes()).toContain('font-heading')
    expect(css).toMatch(/--font-heading:[^;]*\bserif;/)
  })

  it('uses system fonts only', () => {
    expect(css).not.toMatch(/@font-face|@import\s+url\(|fonts\.googleapis/)
  })

  it('shows the title, then the question form, then the scope and exclusions', async () => {
    ;({ wrapper } = await mountWithPlugins(HomeView))
    const html = wrapper.html()
    const order = ['<h1', '<form', 'Qué investiga', 'Qué no ofrece'].map((s) => html.indexOf(s))

    expect(order.every((index) => index >= 0)).toBe(true)
    expect(order).toEqual([...order].sort((a, b) => a - b))
    for (const exclusion of [
      'Asesoramiento jurídico o financiero personalizado.',
      'Tasaciones de inmuebles.',
      'Recomendaciones de inversión.',
      'Previsiones sin respaldo en datos.',
    ]) {
      expect(wrapper.text()).toContain(exclusion)
    }
  })

  it('shows the progress panel between the form and the examples', async () => {
    submitResearch.mockResolvedValue({
      first: { kind: 'task', taskId: 't', contextId: 'c', state: 'TASK_STATE_SUBMITTED', text: '' },
      events: { next: vi.fn<ResearchSubmission['events']['next']>(() => new Promise(() => {})) },
      close: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
    })
    ;({ wrapper } = await mountWithPlugins(HomeView))
    expect(wrapper.find('[data-testid="research-progress"]').exists()).toBe(false)

    await wrapper.find('textarea').setValue('¿Cómo están los alquileres?')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const html = wrapper.html()
    const order = ['</form>', 'data-testid="research-progress"', 'examples-heading'].map((s) =>
      html.indexOf(s),
    )
    expect(order.every((index) => index >= 0)).toBe(true)
    expect(order).toEqual([...order].sort((a, b) => a - b))
  })

  it('fills and focuses the field from an example without sending it', async () => {
    ;({ wrapper } = await mountWithPlugins(HomeView, { attachTo: document.body }))
    const textarea = wrapper.find<HTMLTextAreaElement>('textarea')

    await wrapper.find('form').trigger('submit')
    expect(wrapper.find('#research-status').text()).toBe('Escribe una pregunta.')

    const example = wrapper.findAll('section[aria-labelledby="examples-heading"] button')[0]!
    await example.trigger('click')

    expect(textarea.element.value).toBe(example.text())
    expect(document.activeElement).toBe(textarea.element)
    expect(wrapper.find('#research-status').text()).toBe('')
    expect(textarea.attributes('aria-invalid')).toBeUndefined()
    expect(submitResearch).not.toHaveBeenCalled()
  })

  it('replaces a draft with the chosen example', async () => {
    ;({ wrapper } = await mountWithPlugins(HomeView))
    const textarea = wrapper.find<HTMLTextAreaElement>('textarea')
    await textarea.setValue('Mi borrador')

    const example = wrapper.findAll('section[aria-labelledby="examples-heading"] button')[1]!
    await example.trigger('click')
    expect(textarea.element.value).toBe(example.text())
  })
})

describe('Motion', () => {
  // App views and components; vendored primitives in ui/ animate overlays on open/close.
  function* appSources(dir: string): Generator<string> {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name)
      if (entry.isDirectory() && entry.name !== 'ui') yield* appSources(path)
      else if (entry.name.endsWith('.vue')) yield path
    }
  }

  it('runs decorative animation only when motion is allowed', () => {
    const files = ['src/views', 'src/components', 'src/App.vue'].flatMap((p) =>
      p.endsWith('.vue') ? [p] : [...appSources(p)],
    )
    const unguarded = files.flatMap((file) =>
      [...readFileSync(file, 'utf8').matchAll(/(\S*)\b(animate-[\w-]+|transition-[\w-]+)/g)]
        .filter(([, prefix]) => !prefix!.includes('motion-safe:'))
        .map(([match]) => `${file}: ${match}`),
    )
    expect(files.length).toBeGreaterThan(3)
    expect(unguarded).toEqual([])
  })
})
