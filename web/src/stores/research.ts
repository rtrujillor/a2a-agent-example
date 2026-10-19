import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { a2aService } from '@/services/a2aClient'
import {
  MAX_QUESTION_LENGTH,
  type Outcome,
  type ProgressPhase,
  type ProgressStep,
  type ReplyStatus,
  type ResearchEvent,
  type ResearchSubmission,
  type SubmissionStatus,
  type TaskStateName,
  type ValidationError,
} from '@/types/research'

// Final and interrupted task states, and how the panel presents each.
const OUTCOMES: Partial<Record<TaskStateName, Outcome>> = {
  TASK_STATE_INPUT_REQUIRED: 'inputRequired',
  TASK_STATE_COMPLETED: 'completed',
  TASK_STATE_REJECTED: 'rejected',
  TASK_STATE_FAILED: 'failed',
  // The agent never sends these today; show them as a failure.
  TASK_STATE_CANCELED: 'failed',
  TASK_STATE_AUTH_REQUIRED: 'failed',
}

// Submission of one research question, then its progress until an outcome,
// including replies to the agent's clarifying question.
export const useResearchStore = defineStore('research', () => {
  const question = ref('')
  const status = ref<SubmissionStatus>('idle')
  const validationError = ref<ValidationError>()
  const taskId = ref<string>()
  const contextId = ref<string>()

  const steps = ref<ProgressStep[]>([])
  const phase = ref<ProgressPhase>('idle')
  const replyText = ref('')
  const replyStatus = ref<ReplyStatus>('idle')
  const replyError = ref<ValidationError>()

  // The open stream of the accepted request; not reactive state.
  let current: ResearchSubmission | undefined
  // Bumped by every new request, so a closed stream's late events are ignored.
  let generation = 0
  let following: Promise<void> = Promise.resolve()

  const isSubmitting = computed(() => status.value === 'submitting')
  const canSubmit = computed(() => !isSubmitting.value)
  const showProgress = computed(() => phase.value !== 'idle' || steps.value.length > 0)
  const isWorking = computed(() => phase.value === 'working')
  const isReplying = computed(() => replyStatus.value === 'sending')

  function validate(text: string): ValidationError | undefined {
    if (text.length === 0) return 'empty'
    if (text.length > MAX_QUESTION_LENGTH) return 'tooLong'
    return undefined
  }

  function clearProgress() {
    generation += 1
    steps.value = []
    phase.value = 'idle'
    replyText.value = ''
    replyStatus.value = 'idle'
    replyError.value = undefined
  }

  async function closeCurrent() {
    const previous = current
    current = undefined
    taskId.value = undefined
    contextId.value = undefined
    await previous?.close()
  }

  function apply(event: ResearchEvent) {
    if (event.kind === 'artifact') return
    if (event.kind === 'message') {
      if (event.text) steps.value.push({ kind: 'agent', text: event.text })
      return
    }
    const outcome = OUTCOMES[event.state]
    if (outcome) {
      steps.value.push({ kind: 'outcome', outcome, text: event.text })
      phase.value = outcome === 'inputRequired' ? 'inputRequired' : 'finished'
      return
    }
    phase.value = 'working'
    if (event.text) steps.value.push({ kind: 'agent', text: event.text })
  }

  // Reads the stream until an outcome; a stream that stops first counts as lost.
  async function follow(submission: ResearchSubmission, gen: number) {
    try {
      apply(submission.first)
      while (gen === generation && phase.value === 'working') {
        const result = await submission.events.next()
        if (gen !== generation || result.done) break
        apply(result.value)
      }
    } catch {
      // Reported below as a lost connection; raw errors are never shown.
    }
    if (gen === generation && phase.value === 'working') {
      steps.value.push({ kind: 'lost' })
      phase.value = 'finished'
    }
  }

  async function submit() {
    if (isSubmitting.value) return
    const text = question.value.trim()
    validationError.value = validate(text)
    if (validationError.value) {
      status.value = 'invalid'
      return
    }

    status.value = 'submitting'
    clearProgress()
    await closeCurrent()
    const gen = generation
    try {
      current = await a2aService.submitResearch(text)
      const { first } = current
      taskId.value = first.kind === 'message' ? undefined : first.taskId
      contextId.value = first.contextId
      status.value = 'submitted'
      following = follow(current, gen)
    } catch {
      status.value = 'unreachable'
    }
  }

  // Answers the agent's clarifying question on the same task.
  async function reply() {
    if (isReplying.value || phase.value !== 'inputRequired') return
    if (!taskId.value || !contextId.value) return
    const text = replyText.value.trim()
    replyError.value = validate(text)
    if (replyError.value) {
      replyStatus.value = 'invalid'
      return
    }

    replyStatus.value = 'sending'
    const gen = generation
    try {
      const submission = await a2aService.replyToTask(
        { taskId: taskId.value, contextId: contextId.value },
        text,
      )
      if (gen !== generation) {
        await submission.close()
        return
      }
      const previous = current
      current = submission
      await previous?.close()
      steps.value.push({ kind: 'user', text })
      replyText.value = ''
      replyStatus.value = 'idle'
      phase.value = 'working'
      following = follow(submission, gen)
    } catch {
      if (gen === generation) replyStatus.value = 'unreachable'
    }
  }

  // Fills the field with an example question without sending it. A request
  // in flight keeps its busy status, so it cannot be submitted twice.
  function applyExample(text: string) {
    question.value = text
    validationError.value = undefined
    if (!isSubmitting.value) status.value = 'idle'
  }

  async function reset() {
    clearProgress()
    await closeCurrent()
    question.value = ''
    status.value = 'idle'
    validationError.value = undefined
  }

  // For tests: resolves once the current stream has been read to its end.
  function settled() {
    return following
  }

  return {
    question,
    status,
    validationError,
    taskId,
    contextId,
    steps,
    phase,
    replyText,
    replyStatus,
    replyError,
    isSubmitting,
    canSubmit,
    showProgress,
    isWorking,
    isReplying,
    submit,
    reply,
    applyExample,
    reset,
    settled,
  }
})
