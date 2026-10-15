import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { a2aService } from '@/services/a2aClient'
import {
  MAX_QUESTION_LENGTH,
  type ResearchSubmission,
  type SubmissionStatus,
  type ValidationError,
} from '@/types/research'

// Submission of one research question. Ends when the agent accepts it;
// progress handling reads the accepted stream later.
export const useResearchStore = defineStore('research', () => {
  const question = ref('')
  const status = ref<SubmissionStatus>('idle')
  const validationError = ref<ValidationError>()
  const taskId = ref<string>()
  const contextId = ref<string>()

  // The open stream of the accepted request; not reactive state.
  let current: ResearchSubmission | undefined

  const isSubmitting = computed(() => status.value === 'submitting')
  const canSubmit = computed(() => !isSubmitting.value)

  function validate(text: string): ValidationError | undefined {
    if (text.length === 0) return 'empty'
    if (text.length > MAX_QUESTION_LENGTH) return 'tooLong'
    return undefined
  }

  async function closeCurrent() {
    const previous = current
    current = undefined
    taskId.value = undefined
    contextId.value = undefined
    await previous?.close()
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
    await closeCurrent()
    try {
      current = await a2aService.submitResearch(text)
      const { first } = current
      taskId.value = first.kind === 'message' ? undefined : first.taskId
      contextId.value = first.contextId
      status.value = 'submitted'
    } catch {
      status.value = 'unreachable'
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
    await closeCurrent()
    question.value = ''
    status.value = 'idle'
    validationError.value = undefined
  }

  return {
    question,
    status,
    validationError,
    taskId,
    contextId,
    isSubmitting,
    canSubmit,
    submit,
    applyExample,
    reset,
  }
})
