import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'

import ResearchProgress from '@/components/ResearchProgress.vue'
import { AgentUnavailableError, a2aService } from '@/services/a2aClient'
import { useResearchStore } from '@/stores/research'
import { mountWithPlugins } from '@/test-utils/mount'
import type { ResearchEvent, ResearchSubmission, TaskIds } from '@/types/research'

vi.mock('@/services/a2aClient', () => ({
  AgentUnavailableError: class AgentUnavailableError extends Error {},
  a2aService: {
    submitResearch: vi.fn<(text: string) => Promise<ResearchSubmission>>(),
    replyToTask: vi.fn<(ids: TaskIds, text: string) => Promise<ResearchSubmission>>(),
  },
}))

const submitResearch = vi.mocked(a2aService.submitResearch)
const replyToTask = vi.mocked(a2aService.replyToTask)

const QUESTION = '¿Compra o alquiler, y en qué zona?'

const status = (state: string, text = ''): ResearchEvent => ({
  kind: 'status',
  taskId: 'task-1',
  contextId: 'ctx-1',
  state,
  text,
})

const submitted: ResearchEvent = {
  kind: 'task',
  taskId: 'task-1',
  contextId: 'ctx-1',
  state: 'TASK_STATE_SUBMITTED',
  text: '',
}

// A submission whose remaining events come from `script`, then the stream ends.
function scripted(first: ResearchEvent, script: ResearchEvent[]): ResearchSubmission {
  const items = [...script]
  return {
    first,
    events: {
      next: vi.fn<ResearchSubmission['events']['next']>(async () => {
        const item = items.shift()
        return item ? { done: false, value: item } : { done: true, value: undefined }
      }),
    },
    close: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
  }
}

let wrapper: VueWrapper

async function mountPanel() {
  ;({ wrapper } = await mountWithPlugins(ResearchProgress, { attachTo: document.body }))
  return useResearchStore()
}

async function run(script: ResearchEvent[]) {
  const store = await mountPanel()
  submitResearch.mockResolvedValue(scripted(submitted, script))
  store.question = '¿Y los precios?'
  await store.submit()
  await store.settled()
  await flushPromises()
  return store
}

const panel = () => wrapper.find('[data-testid="research-progress"]')
const outcome = (name: string) => wrapper.find(`[data-outcome="${name}"]`)

describe('ResearchProgress', () => {
  beforeEach(() => {
    submitResearch.mockReset()
    replyToTask.mockReset()
  })
  afterEach(() => wrapper?.unmount())

  it('is hidden before a request', async () => {
    await mountPanel()
    expect(panel().exists()).toBe(false)
  })

  it('shows the working indicator while the agent works', async () => {
    const store = await mountPanel()
    const submission = scripted(submitted, [])
    submission.events.next = vi.fn<ResearchSubmission['events']['next']>(
      () => new Promise(() => {}),
    )
    submitResearch.mockResolvedValue(submission)
    store.question = 'Hola'
    await store.submit()
    await flushPromises()

    const working = wrapper.find('[data-testid="progress-working"]')
    expect(working.text()).toBe('Interpretando la pregunta…')
    expect(working.find('svg').exists()).toBe(true)
  })

  it('keeps line breaks and shows markup literally', async () => {
    await run([
      status('TASK_STATE_WORKING', 'Entendido: alquileres.\nSupuestos: <b>texto</b>'),
      status('TASK_STATE_COMPLETED', 'Aún no disponible.'),
    ])

    const agent = wrapper.find('[data-step="agent"]')
    expect(agent.find('.whitespace-pre-line').element.textContent).toBe(
      'Entendido: alquileres.\nSupuestos: <b>texto</b>',
    )
    expect(agent.find('b').exists()).toBe(false)
    expect(wrapper.find('[data-testid="progress-working"]').exists()).toBe(false)
  })

  it.each([
    ['TASK_STATE_COMPLETED', 'completed', 'Solicitud completada', 'bg-card'],
    ['TASK_STATE_REJECTED', 'rejected', 'No se puede investigar esta pregunta', 'bg-notice'],
    ['TASK_STATE_FAILED', 'failed', 'No se pudo completar la solicitud', 'text-destructive'],
  ])('presents %s with its heading and style', async (state, name, title, styleClass) => {
    await run([status(state, 'Texto del agente')])

    const block = outcome(name)
    expect(block.text()).toContain(title)
    expect(block.text()).toContain('Texto del agente')
    expect(block.classes()).toContain(styleClass)
    expect(block.find('svg').exists()).toBe(true)
    // Polite announcer only; outcome blocks don't interrupt as role="alert".
    expect(block.attributes('role')).toBe('group')
  })

  it('shows a fixed text when a failure has none', async () => {
    await run([status('TASK_STATE_CANCELED')])
    expect(outcome('failed').text()).toContain('La solicitud no se pudo completar.')
  })

  it('reports a lost connection and keeps earlier steps', async () => {
    await run([status('TASK_STATE_WORKING', 'Entendido: alquileres.')])

    expect(wrapper.find('[data-step="agent"]').text()).toBe('Entendido: alquileres.')
    const lost = outcome('lost')
    expect(lost.text()).toContain('Se perdió la conexión con el agente')
    expect(lost.classes()).toContain('text-destructive')
  })

  describe('reply', () => {
    async function clarification() {
      return run([status('TASK_STATE_INPUT_REQUIRED', QUESTION)])
    }

    it('offers a labeled reply field, a named button, and a hint', async () => {
      await clarification()

      const block = outcome('inputRequired')
      expect(block.text()).toContain('El agente necesita una aclaración')
      expect(block.text()).toContain(QUESTION)
      expect(block.classes()).toContain('border-primary/40')
      const field = block.find('textarea')
      expect(block.find(`label[for="${field.attributes('id')}"]`).text()).toBe(
        'Tu respuesta a la pregunta del agente',
      )
      expect(block.find('button[type="submit"]').attributes('aria-label')).toBe('Enviar respuesta')
      expect(block.text()).toContain('O escribe una nueva pregunta en el formulario de arriba.')
    })

    it('asks for an answer when the reply is empty', async () => {
      await clarification()
      await wrapper.find('[data-outcome="inputRequired"] form').trigger('submit')

      expect(wrapper.find('#research-reply-status').text()).toBe('Escribe una respuesta.')
      expect(wrapper.find('textarea').attributes('aria-invalid')).toBe('true')
      expect(replyToTask).not.toHaveBeenCalled()
    })

    it('sends on Ctrl+Enter, but not on Enter alone', async () => {
      await clarification()
      replyToTask.mockResolvedValue(scripted(status('TASK_STATE_WORKING'), []))
      const field = wrapper.find('textarea')
      await field.setValue('Alquiler en Bilbao')

      await field.trigger('keydown', { key: 'Enter' })
      expect(replyToTask).not.toHaveBeenCalled()
      await field.trigger('keydown', { key: 'Enter', ctrlKey: true })
      expect(replyToTask).toHaveBeenCalledOnce()
    })

    it('is busy and disabled while sending', async () => {
      await clarification()
      replyToTask.mockReturnValue(new Promise(() => {}))
      await wrapper.find('textarea').setValue('Alquiler')
      await wrapper.find('[data-outcome="inputRequired"] form').trigger('submit')

      const button = wrapper.find('[data-outcome="inputRequired"] button[type="submit"]')
      expect(button.attributes('disabled')).toBeDefined()
      expect(button.attributes('aria-busy')).toBe('true')
    })

    it('shows the reply, removes the field, and follows the next steps', async () => {
      const store = await clarification()
      replyToTask.mockResolvedValue(
        scripted(status('TASK_STATE_WORKING'), [
          status('TASK_STATE_COMPLETED', 'Aún no disponible.'),
        ]),
      )
      await wrapper.find('textarea').setValue('Alquiler en Bilbao')
      await wrapper.find('[data-outcome="inputRequired"] form').trigger('submit')
      await store.settled()
      await flushPromises()

      expect(wrapper.find('[data-step="user"]').text()).toContain('Alquiler en Bilbao')
      expect(wrapper.find('textarea').exists()).toBe(false)
      expect(outcome('completed').exists()).toBe(true)
    })

    it('offers a new reply field for a second question', async () => {
      const store = await clarification()
      replyToTask.mockResolvedValue(
        scripted(status('TASK_STATE_WORKING'), [
          status('TASK_STATE_INPUT_REQUIRED', '¿En qué municipio?'),
        ]),
      )
      await wrapper.find('textarea').setValue('Alquiler')
      await wrapper.find('[data-outcome="inputRequired"] form').trigger('submit')
      await store.settled()
      await flushPromises()

      const questions = wrapper.findAll('[data-outcome="inputRequired"]')
      expect(questions).toHaveLength(2)
      expect(questions[0]!.find('textarea').exists()).toBe(false)
      expect(questions[1]!.find('textarea').exists()).toBe(true)
    })

    it('keeps the reply and shows the connection error when the agent is unavailable', async () => {
      await clarification()
      replyToTask.mockRejectedValue(new AgentUnavailableError())
      await wrapper.find('textarea').setValue('Alquiler en Bilbao')
      await wrapper.find('[data-outcome="inputRequired"] form').trigger('submit')
      await flushPromises()

      expect(wrapper.find<HTMLTextAreaElement>('textarea').element.value).toBe(
        'Alquiler en Bilbao',
      )
      expect(wrapper.find('#research-reply-status').text()).toBe(
        'No se pudo conectar con el agente. Inténtalo de nuevo más tarde.',
      )
    })
  })

  it('announces the newest step politely without moving focus', async () => {
    const outside = document.createElement('button')
    document.body.append(outside)
    outside.focus()

    await run([
      status('TASK_STATE_WORKING', 'Entendido: alquileres.'),
      status('TASK_STATE_REJECTED', 'No es vivienda.'),
    ])

    const announcement = wrapper.find('[data-testid="progress-announcement"]')
    expect(announcement.attributes('aria-live')).toBe('polite')
    expect(announcement.text()).toBe('No se puede investigar esta pregunta. No es vivienda.')
    expect(document.activeElement).toBe(outside)
    outside.remove()
  })
})
