// A2A client: agent-card discovery, sending research tasks, and streaming task updates.
// The only module that imports @a2a-js/sdk; it exposes the types in types/research.ts.
import { Role, taskStateToJSON, type Part, type StreamResponse } from '@a2a-js/sdk'
import {
  ClientFactory,
  ClientFactoryOptions,
  DefaultAgentCardResolver,
  JsonRpcTransportFactory,
  RestTransportFactory,
  type Client,
} from '@a2a-js/sdk/client'
import type { ResearchEvent, ResearchSubmission, TaskIds } from '@/types/research'

// Any failure before the agent accepts a request. `reason` holds the original
// error for debugging only; it is never shown to the user.
export class AgentUnavailableError extends Error {
  constructor(readonly reason?: unknown) {
    super('Agent unavailable')
    this.name = 'AgentUnavailableError'
  }
}

export interface A2AServiceOptions {
  agentUrl: string
  fetchImpl?: typeof fetch
}

export interface A2AService {
  // A new request: no task or context identifier.
  submitResearch(text: string): Promise<ResearchSubmission>
  // A reply to the agent's clarifying question, on that task's identifiers.
  replyToTask(ids: TaskIds, text: string): Promise<ResearchSubmission>
}

function messageText(parts: Part[] | undefined): string {
  return (parts ?? [])
    .map((part) => (part.content?.$case === 'text' ? part.content.value : ''))
    .join('')
}

function toResearchEvent(response: StreamResponse): ResearchEvent | undefined {
  const payload = response.payload
  switch (payload?.$case) {
    case 'task': {
      const { id, contextId, status } = payload.value
      const text = messageText(status?.message?.parts)
      return { kind: 'task', taskId: id, contextId, state: stateName(status?.state), text }
    }
    case 'statusUpdate': {
      const { taskId, contextId, status } = payload.value
      const text = messageText(status?.message?.parts)
      return { kind: 'status', taskId, contextId, state: stateName(status?.state), text }
    }
    case 'artifactUpdate': {
      const { taskId, contextId } = payload.value
      return { kind: 'artifact', taskId, contextId }
    }
    case 'message': {
      const { contextId, parts } = payload.value
      return { kind: 'message', contextId, text: messageText(parts) }
    }
    default:
      return undefined
  }
}

function stateName(state: number | undefined): string {
  return state === undefined ? 'TASK_STATE_UNSPECIFIED' : taskStateToJSON(state)
}

async function* mapEvents(stream: AsyncGenerator<StreamResponse>): AsyncGenerator<ResearchEvent> {
  for await (const response of stream) {
    const event = toResearchEvent(response)
    if (event) yield event
  }
}

export function createA2AService({ agentUrl, fetchImpl }: A2AServiceOptions): A2AService {
  const fetchOption = fetchImpl ? { fetchImpl } : {}
  const factory = new ClientFactory(
    ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
      transports: [new JsonRpcTransportFactory(fetchOption), new RestTransportFactory(fetchOption)],
      cardResolver: new DefaultAgentCardResolver(fetchOption),
    }),
  )
  let client: Promise<Client> | undefined

  async function send(text: string, ids: TaskIds): Promise<ResearchSubmission> {
    try {
      client ??= factory.createFromUrl(agentUrl)
      const stream = (await client).sendMessageStream({
        tenant: '',
        message: {
          messageId: crypto.randomUUID(),
          contextId: ids.contextId,
          taskId: ids.taskId,
          role: Role.ROLE_USER,
          parts: [
            {
              content: { $case: 'text', value: text },
              filename: '',
              mediaType: 'text/plain',
              metadata: undefined,
            },
          ],
          metadata: undefined,
          extensions: [],
          referenceTaskIds: [],
        },
        configuration: undefined,
        metadata: undefined,
      })
      const events = mapEvents(stream)
      const first = await events.next()
      if (first.done) throw new Error('Stream ended before the first event')
      return {
        first: first.value,
        events,
        close: async () => {
          await events.return(undefined)
        },
      }
    } catch (error) {
      // Read the agent card again next time, e.g. when the agent starts later.
      client = undefined
      throw new AgentUnavailableError(error)
    }
  }

  return {
    submitResearch: (text) => send(text, { taskId: '', contextId: '' }),
    replyToTask: (ids, text) => send(text, ids),
  }
}

export const a2aService = createA2AService({ agentUrl: import.meta.env.VITE_AGENT_URL })
