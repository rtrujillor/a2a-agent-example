// Client-side types for research requests, task status, answers, and citations.
// SDK types stay inside services/a2aClient.ts; everything else uses these.

// Mirrors the agent's message-length limit; the server enforces its own cap
// from configuration and stays the authority. Keep both in sync.
export const MAX_QUESTION_LENGTH = 2000

export type SubmissionStatus = 'idle' | 'invalid' | 'submitting' | 'submitted' | 'unreachable'

export type ValidationError = 'empty' | 'tooLong'

// One stream event. `state` is the A2A task-state name (e.g. 'TASK_STATE_WORKING').
export type ResearchEvent =
  | { kind: 'task'; taskId: string; contextId: string; state: string }
  | { kind: 'status'; taskId: string; contextId: string; state: string }
  | { kind: 'artifact'; taskId: string; contextId: string }
  | { kind: 'message'; contextId: string; text: string }

// An accepted request: its first event, the rest of the stream, and a way to close it.
export interface ResearchSubmission {
  first: ResearchEvent
  events: AsyncIterator<ResearchEvent>
  close(): Promise<void>
}
