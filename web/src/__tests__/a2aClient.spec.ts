import { describe, expect, it, vi } from 'vitest'
import { AgentUnavailableError, createA2AService } from '@/services/a2aClient'

const AGENT_URL = 'http://agent.test'
const CARD_URL = `${AGENT_URL}/.well-known/agent-card.json`
const RPC_URL = `${AGENT_URL}/a2a`

// A 1.x agent card with one JSON-RPC interface and streaming enabled.
const agentCard = {
  name: 'Spain Housing Access Agent',
  description: 'Research agent',
  version: '0.1.0',
  supportedInterfaces: [{ url: RPC_URL, protocolBinding: 'JSONRPC', protocolVersion: '1.0' }],
  capabilities: { streaming: true },
  defaultInputModes: ['text/plain'],
  defaultOutputModes: ['text/plain'],
  skills: [],
}

const submittedTask = {
  task: { id: 'task-1', contextId: 'ctx-1', status: { state: 'TASK_STATE_SUBMITTED' } },
}

interface RpcRequest {
  id: number
  method: string
  params: { message: Record<string, unknown> }
}

type StreamMode = { results: unknown[]; keepOpen?: boolean }

function sseBody(id: number, { results, keepOpen = false }: StreamMode) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const result of results) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ jsonrpc: '2.0', id, result })}\n\n`),
        )
      }
      if (!keepOpen) controller.close()
    },
  })
}

// Fake fetch: serves the card and answers SendStreamingMessage with an SSE stream.
function fakeAgent({
  card = agentCard as unknown,
  stream = { results: [submittedTask] } as StreamMode,
} = {}) {
  const rpcRequests: { request: RpcRequest; headers: Headers }[] = []
  const fetchImpl = vi.fn<typeof fetch>(async (input, init) => {
    const url = String(input)
    if (url === CARD_URL) return Response.json(card)
    if (url === RPC_URL) {
      const request = JSON.parse(String(init?.body)) as RpcRequest
      rpcRequests.push({ request, headers: new Headers(init?.headers) })
      return new Response(sseBody(request.id, stream), {
        headers: { 'Content-Type': 'text/event-stream' },
      })
    }
    return new Response('not found', { status: 404 })
  })
  return { fetchImpl, calls: fetchImpl.mock.calls, rpcRequests }
}

describe('a2aClient', () => {
  it('reads the agent card under the agent URL', async () => {
    const agent = fakeAgent()
    await createA2AService({ agentUrl: AGENT_URL, fetchImpl: agent.fetchImpl }).submitResearch(
      'Hola',
    )
    expect(String(agent.calls[0]?.[0])).toBe(CARD_URL)
  })

  it('sends one text part with no task or context id and no credentials', async () => {
    const agent = fakeAgent()
    await createA2AService({ agentUrl: AGENT_URL, fetchImpl: agent.fetchImpl }).submitResearch(
      '¿Cuánto ha subido el alquiler en Madrid?',
    )

    expect(agent.rpcRequests).toHaveLength(1)
    const { request, headers } = agent.rpcRequests[0]!
    expect(request.method).toBe('SendStreamingMessage')
    const message = request.params.message
    expect(message.role).toBe('ROLE_USER')
    expect(message.parts).toEqual([
      expect.objectContaining({ text: '¿Cuánto ha subido el alquiler en Madrid?' }),
    ])
    expect(message.taskId ?? '').toBe('')
    expect(message.contextId ?? '').toBe('')
    expect(headers.has('Authorization')).toBe(false)
  })

  it('resolves with the ids of the first task event', async () => {
    const agent = fakeAgent()
    const submission = await createA2AService({
      agentUrl: AGENT_URL,
      fetchImpl: agent.fetchImpl,
    }).submitResearch('Hola')
    expect(submission.first).toEqual({
      kind: 'task',
      taskId: 'task-1',
      contextId: 'ctx-1',
      state: 'TASK_STATE_SUBMITTED',
    })
  })

  it.each([
    ['an invalid agent card', () => fakeAgent({ card: { hello: 'world' } }).fetchImpl],
    [
      'a rejected fetch',
      () => vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed to fetch')),
    ],
    ['an empty stream', () => fakeAgent({ stream: { results: [] } }).fetchImpl],
  ])('throws AgentUnavailableError on %s', async (_label, makeFetch) => {
    const service = createA2AService({ agentUrl: AGENT_URL, fetchImpl: makeFetch() })
    await expect(service.submitResearch('Hola')).rejects.toBeInstanceOf(AgentUnavailableError)
  })

  it('reads the agent card again after a failure', async () => {
    const agent = fakeAgent()
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockImplementation(agent.fetchImpl)
    const service = createA2AService({ agentUrl: AGENT_URL, fetchImpl })

    await expect(service.submitResearch('Hola')).rejects.toBeInstanceOf(AgentUnavailableError)
    await expect(service.submitResearch('Hola')).resolves.toBeDefined()
    const cardReads = fetchImpl.mock.calls.filter(([input]) => String(input) === CARD_URL)
    expect(cardReads).toHaveLength(2)
  })

  it('close() ends the event stream', async () => {
    const agent = fakeAgent({ stream: { results: [submittedTask], keepOpen: true } })
    const submission = await createA2AService({
      agentUrl: AGENT_URL,
      fetchImpl: agent.fetchImpl,
    }).submitResearch('Hola')

    await submission.close()
    await expect(submission.events.next()).resolves.toEqual({ done: true, value: undefined })
  })
})
