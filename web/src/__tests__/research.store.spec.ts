import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AgentUnavailableError, a2aService } from '@/services/a2aClient'
import { useResearchStore } from '@/stores/research'
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

const status = (state: string, text = ''): ResearchEvent => ({
  kind: 'status',
  taskId: 'task-1',
  contextId: 'ctx-1',
  state,
  text,
})

// A submission whose remaining events are the script; an Error item is thrown.
function scripted(first: ResearchEvent, script: (ResearchEvent | Error)[]): ResearchSubmission {
  const items = [...script]
  return {
    first,
    events: {
      next: vi.fn<ResearchSubmission['events']['next']>(async () => {
        const item = items.shift()
        if (item instanceof Error) throw item
        return item ? { done: false, value: item } : { done: true, value: undefined }
      }),
    },
    close: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
  }
}

const submitted: ResearchEvent = {
  kind: 'task',
  taskId: 'task-1',
  contextId: 'ctx-1',
  state: 'TASK_STATE_SUBMITTED',
  text: '',
}

function accepted(taskId = 'task-1', contextId = 'ctx-1'): ResearchSubmission {
  return {
    first: { kind: 'task', taskId, contextId, state: 'TASK_STATE_SUBMITTED', text: '' },
    events: { next: vi.fn<ResearchSubmission['events']['next']>() },
    close: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
  }
}

describe('research store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    submitResearch.mockReset()
    replyToTask.mockReset()
  })

  it.each([
    ['empty', '', 'empty'],
    ['whitespace-only', '  \n\t ', 'empty'],
    ['over 2,000 characters', 'a'.repeat(2001), 'tooLong'],
  ])('rejects an %s question without calling the agent', async (_label, text, error) => {
    const store = useResearchStore()
    store.question = text
    await store.submit()

    expect(store.status).toBe('invalid')
    expect(store.validationError).toBe(error)
    expect(store.question).toBe(text)
    expect(submitResearch).not.toHaveBeenCalled()
  })

  it('accepts exactly 2,000 characters', async () => {
    submitResearch.mockResolvedValue(accepted())
    const store = useResearchStore()
    store.question = 'a'.repeat(2000)
    await store.submit()
    expect(submitResearch).toHaveBeenCalledOnce()
    expect(store.status).toBe('submitted')
  })

  it('trims the question and keeps the ids on acceptance', async () => {
    submitResearch.mockResolvedValue(accepted())
    const store = useResearchStore()
    store.question = '\n  ¿Precio medio del alquiler en Valencia?  \n'
    await store.submit()

    expect(submitResearch).toHaveBeenCalledWith('¿Precio medio del alquiler en Valencia?')
    expect(store.status).toBe('submitted')
    expect(store.validationError).toBeUndefined()
    expect(store.taskId).toBe('task-1')
    expect(store.contextId).toBe('ctx-1')
  })

  it('becomes unreachable on AgentUnavailableError, keeps the question, and allows a retry', async () => {
    submitResearch.mockRejectedValueOnce(new AgentUnavailableError())
    const store = useResearchStore()
    store.question = 'Hola'
    await store.submit()

    expect(store.status).toBe('unreachable')
    expect(store.question).toBe('Hola')
    expect(store.canSubmit).toBe(true)

    submitResearch.mockResolvedValueOnce(accepted())
    await store.submit()
    expect(store.status).toBe('submitted')
  })

  it('ignores a second submit while one is in flight', async () => {
    let resolve!: (value: ResearchSubmission) => void
    submitResearch.mockReturnValue(new Promise((r) => (resolve = r)))
    const store = useResearchStore()
    store.question = 'Hola'

    const first = store.submit()
    expect(store.isSubmitting).toBe(true)
    expect(store.canSubmit).toBe(false)
    await store.submit()
    resolve(accepted())
    await first

    expect(submitResearch).toHaveBeenCalledOnce()
  })

  it('closes the previous stream and clears the ids before a new submission', async () => {
    const previous = accepted('task-1', 'ctx-1')
    submitResearch.mockResolvedValueOnce(previous)
    const store = useResearchStore()
    store.question = 'Primera'
    await store.submit()

    let resolve!: (value: ResearchSubmission) => void
    submitResearch.mockReturnValueOnce(new Promise((r) => (resolve = r)))
    store.question = 'Segunda'
    const second = store.submit()
    await vi.waitFor(() => expect(submitResearch).toHaveBeenCalledTimes(2))

    expect(previous.close).toHaveBeenCalledOnce()
    expect(store.taskId).toBeUndefined()
    expect(store.contextId).toBeUndefined()

    resolve(accepted('task-2', 'ctx-2'))
    await second
    expect(store.taskId).toBe('task-2')
  })

  describe('applyExample', () => {
    it('fills the question, clears a validation error, and sends nothing', async () => {
      const store = useResearchStore()
      await store.submit()
      expect(store.status).toBe('invalid')

      store.applyExample('¿Cuánto ha subido el alquiler en Madrid?')

      expect(store.question).toBe('¿Cuánto ha subido el alquiler en Madrid?')
      expect(store.status).toBe('idle')
      expect(store.validationError).toBeUndefined()
      expect(submitResearch).not.toHaveBeenCalled()
    })

    it('keeps the busy status while a request is in flight', async () => {
      let resolve!: (submission: ResearchSubmission) => void
      submitResearch.mockReturnValue(new Promise((r) => (resolve = r)))
      const store = useResearchStore()
      store.question = 'Primera pregunta'
      const pending = store.submit()

      store.applyExample('Otra pregunta')
      expect(store.status).toBe('submitting')
      expect(store.canSubmit).toBe(false)

      resolve(accepted())
      await pending
    })
  })

  describe('progress', () => {
    async function run(script: (ResearchEvent | Error)[]) {
      const store = useResearchStore()
      submitResearch.mockResolvedValue(scripted(submitted, script))
      store.question = '¿Cómo están los alquileres?'
      await store.submit()
      await store.settled()
      return store
    }

    it('shows nothing before a request', () => {
      const store = useResearchStore()
      expect(store.showProgress).toBe(false)
      expect(store.steps).toEqual([])
    })

    it('is working without a step while the agent sends no text', async () => {
      const store = useResearchStore()
      let release!: () => void
      const blocked = new Promise<IteratorResult<ResearchEvent>>((resolve) => {
        release = () => resolve({ done: false, value: status('TASK_STATE_COMPLETED', 'Hecho') })
      })
      const submission = scripted(submitted, [])
      submission.events.next = vi
        .fn<ResearchSubmission['events']['next']>()
        .mockResolvedValueOnce({ done: false, value: status('TASK_STATE_WORKING') })
        .mockReturnValueOnce(blocked)
      submitResearch.mockResolvedValue(submission)
      store.question = 'Hola'
      await store.submit()
      await vi.waitFor(() => expect(submission.events.next).toHaveBeenCalledTimes(2))

      expect(store.phase).toBe('working')
      expect(store.isWorking).toBe(true)
      expect(store.showProgress).toBe(true)
      expect(store.steps).toEqual([])

      release()
      await store.settled()
      expect(store.isWorking).toBe(false)
    })

    it('adds the interpretation and the completed outcome', async () => {
      const store = await run([
        status('TASK_STATE_WORKING'),
        status('TASK_STATE_WORKING', 'Entendido: alquileres.\nSupuestos: España.'),
        status('TASK_STATE_COMPLETED', 'Aún no disponible.'),
      ])

      expect(store.steps).toEqual([
        { kind: 'agent', text: 'Entendido: alquileres.\nSupuestos: España.' },
        { kind: 'outcome', outcome: 'completed', text: 'Aún no disponible.' },
      ])
      expect(store.phase).toBe('finished')
    })

    it.each([
      ['TASK_STATE_INPUT_REQUIRED', 'inputRequired', 'inputRequired'],
      ['TASK_STATE_REJECTED', 'rejected', 'finished'],
      ['TASK_STATE_FAILED', 'failed', 'finished'],
      ['TASK_STATE_CANCELED', 'failed', 'finished'],
    ])('maps %s to the %s outcome', async (state, outcome, phase) => {
      const store = await run([status(state, 'Texto del agente')])

      expect(store.steps).toEqual([{ kind: 'outcome', outcome, text: 'Texto del agente' }])
      expect(store.phase).toBe(phase)
    })

    it.each([
      ['ends', [status('TASK_STATE_WORKING', 'Entendido.')]],
      ['throws', [status('TASK_STATE_WORKING', 'Entendido.'), new Error('network down')]],
    ])('adds a lost step when the stream %s before an outcome', async (_label, script) => {
      const store = await run(script)

      expect(store.steps).toEqual([{ kind: 'agent', text: 'Entendido.' }, { kind: 'lost' }])
      expect(store.phase).toBe('finished')
    })

    it('clears the steps on a new submit and ignores the old stream', async () => {
      const store = useResearchStore()
      let release!: () => void
      const old = scripted(submitted, [])
      old.events.next = vi.fn<ResearchSubmission['events']['next']>(
        () =>
          new Promise((resolve) => {
            release = () =>
              resolve({ done: false, value: status('TASK_STATE_REJECTED', 'Tarde') })
          }),
      )
      submitResearch.mockResolvedValueOnce(old)
      store.question = 'Primera'
      await store.submit()
      await vi.waitFor(() => expect(old.events.next).toHaveBeenCalled())
      const firstRun = store.settled()

      submitResearch.mockResolvedValueOnce(
        scripted(submitted, [status('TASK_STATE_COMPLETED', 'Nueva')]),
      )
      store.question = 'Segunda'
      await store.submit()
      await store.settled()
      release()
      await firstRun

      expect(old.close).toHaveBeenCalled()
      expect(store.steps).toEqual([{ kind: 'outcome', outcome: 'completed', text: 'Nueva' }])
    })
  })

  describe('reply', () => {
    async function askedForClarification() {
      const store = useResearchStore()
      submitResearch.mockResolvedValue(
        scripted(submitted, [status('TASK_STATE_INPUT_REQUIRED', '¿Compra o alquiler?')]),
      )
      store.question = '¿Y los precios?'
      await store.submit()
      await store.settled()
      return store
    }

    it.each([
      ['empty', '   ', 'empty'],
      ['too long', 'a'.repeat(2001), 'tooLong'],
    ])('rejects an %s reply without calling the agent', async (_label, text, error) => {
      const store = await askedForClarification()
      store.replyText = text
      await store.reply()

      expect(store.replyStatus).toBe('invalid')
      expect(store.replyError).toBe(error)
      expect(replyToTask).not.toHaveBeenCalled()
    })

    it('sends the trimmed reply on the task ids and keeps earlier steps', async () => {
      const store = await askedForClarification()
      replyToTask.mockResolvedValue(
        scripted(status('TASK_STATE_WORKING'), [
          status('TASK_STATE_WORKING', 'Entendido: alquiler en Bilbao.'),
          status('TASK_STATE_COMPLETED', 'Aún no disponible.'),
        ]),
      )
      store.replyText = '  Alquiler en Bilbao \n'
      await store.reply()
      await store.settled()

      expect(replyToTask).toHaveBeenCalledWith(
        { taskId: 'task-1', contextId: 'ctx-1' },
        'Alquiler en Bilbao',
      )
      expect(store.steps.map((step) => step.kind)).toEqual(['outcome', 'user', 'agent', 'outcome'])
      expect(store.steps[1]).toEqual({ kind: 'user', text: 'Alquiler en Bilbao' })
      expect(store.replyText).toBe('')
      expect(store.phase).toBe('finished')
    })

    it('ignores a second reply while one is being sent', async () => {
      const store = await askedForClarification()
      let resolve!: (submission: ResearchSubmission) => void
      replyToTask.mockReturnValue(new Promise((r) => (resolve = r)))
      store.replyText = 'Alquiler'
      const first = store.reply()
      await store.reply()
      resolve(scripted(status('TASK_STATE_WORKING'), [status('TASK_STATE_COMPLETED', 'Ok')]))
      await first

      expect(replyToTask).toHaveBeenCalledTimes(1)
    })

    it('keeps the draft and becomes unreachable when the agent is unavailable', async () => {
      const store = await askedForClarification()
      replyToTask.mockRejectedValue(new AgentUnavailableError())
      store.replyText = 'Alquiler en Bilbao'
      await store.reply()

      expect(store.replyStatus).toBe('unreachable')
      expect(store.replyText).toBe('Alquiler en Bilbao')
      expect(store.phase).toBe('inputRequired')
    })
  })
})
