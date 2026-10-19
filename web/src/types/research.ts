// Client-side types for research requests, task status, answers, and citations.
// SDK types stay inside services/a2aClient.ts; everything else uses these.

// Mirrors the agent's message-length limit; the server enforces its own cap
// from configuration and stays the authority. Keep both in sync.
export const MAX_QUESTION_LENGTH = 2000

export type SubmissionStatus = 'idle' | 'invalid' | 'submitting' | 'submitted' | 'unreachable'

export type ValidationError = 'empty' | 'tooLong'

// Source type carried by every citation, as classified by the agent.
export type SourceType = 'official' | 'media' | 'market' | 'other'

// A2A task-state names as the SDK spells them. Unknown names pass through.
export type TaskStateName =
  | 'TASK_STATE_SUBMITTED'
  | 'TASK_STATE_WORKING'
  | 'TASK_STATE_INPUT_REQUIRED'
  | 'TASK_STATE_COMPLETED'
  | 'TASK_STATE_REJECTED'
  | 'TASK_STATE_FAILED'
  | 'TASK_STATE_CANCELED'
  | 'TASK_STATE_AUTH_REQUIRED'
  | (string & {})

// One stream event. `text` is the agent's status message, or '' when there is none.
export type ResearchEvent =
  | { kind: 'task'; taskId: string; contextId: string; state: TaskStateName; text: string }
  | { kind: 'status'; taskId: string; contextId: string; state: TaskStateName; text: string }
  | { kind: 'artifact'; taskId: string; contextId: string }
  | { kind: 'message'; contextId: string; text: string }

// How an accepted request ended, or that it is waiting for the user's reply.
export type Outcome = 'completed' | 'inputRequired' | 'rejected' | 'failed'

// One entry in the progress panel, in arrival order.
export type ProgressStep =
  | { kind: 'agent'; text: string }
  | { kind: 'user'; text: string }
  | { kind: 'outcome'; outcome: Outcome; text: string }
  | { kind: 'lost' }

export type ProgressPhase = 'idle' | 'working' | 'inputRequired' | 'finished'

export type ReplyStatus = 'idle' | 'invalid' | 'sending' | 'unreachable'

// The identifiers of an accepted task, used to reply to it.
export interface TaskIds {
  taskId: string
  contextId: string
}

// An accepted request: its first event, the rest of the stream, and a way to close it.
export interface ResearchSubmission {
  first: ResearchEvent
  events: AsyncIterator<ResearchEvent>
  close(): Promise<void>
}
