import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AgentUnavailableError, a2aService } from '@/services/a2aClient'
import { useResearchStore } from '@/stores/research'
import type { ResearchSubmission } from '@/types/research'

vi.mock('@/services/a2aClient', () => ({
  AgentUnavailableError: class AgentUnavailableError extends Error {},
  a2aService: { submitResearch: vi.fn<(text: string) => Promise<ResearchSubmission>>() },
}))

const submitResearch = vi.mocked(a2aService.submitResearch)

function accepted(taskId = 'task-1', contextId = 'ctx-1'): ResearchSubmission {
  return {
    first: { kind: 'task', taskId, contextId, state: 'TASK_STATE_SUBMITTED' },
    events: { next: vi.fn<ResearchSubmission['events']['next']>() },
    close: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
  }
}

describe('research store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    submitResearch.mockReset()
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
})
