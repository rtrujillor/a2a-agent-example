<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useResearchStore } from '@/stores/research'
import { MAX_QUESTION_LENGTH } from '@/types/research'

const store = useResearchStore()

const validationMessages = {
  empty: 'Escribe una pregunta.',
  tooLong: `La pregunta no puede superar los ${MAX_QUESTION_LENGTH} caracteres.`,
} as const

const statusMessage = computed(() => {
  switch (store.status) {
    case 'invalid':
      return store.validationError ? validationMessages[store.validationError] : ''
    case 'submitting':
      return 'Enviando…'
    case 'submitted':
      return 'Solicitud enviada.'
    case 'unreachable':
      return 'No se pudo conectar con el agente. Inténtalo de nuevo más tarde.'
    default:
      return ''
  }
})

const isError = computed(() => store.status === 'invalid' || store.status === 'unreachable')

// Enter adds a new line; Ctrl+Enter or Cmd+Enter submits.
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    void store.submit()
  }
}
</script>

<template>
  <form class="space-y-3" novalidate @submit.prevent="store.submit()">
    <h2 class="font-heading text-xl font-semibold">Haz tu pregunta</h2>

    <label for="research-question" class="block text-sm font-medium">
      Pregunta sobre el acceso a la vivienda en España
    </label>
    <Textarea
      id="research-question"
      v-model="store.question"
      rows="4"
      :aria-invalid="store.status === 'invalid' ? 'true' : undefined"
      :aria-describedby="store.status === 'invalid' ? 'research-status' : undefined"
      @keydown="onKeydown"
    />

    <div class="flex flex-wrap items-center gap-3">
      <Button type="submit" :disabled="!store.canSubmit" :aria-busy="store.isSubmitting">
        Enviar
      </Button>
      <p
        id="research-status"
        aria-live="polite"
        class="text-sm"
        :class="isError ? 'text-destructive' : 'text-muted-foreground'"
      >
        {{ statusMessage }}
      </p>
    </div>
  </form>
</template>
