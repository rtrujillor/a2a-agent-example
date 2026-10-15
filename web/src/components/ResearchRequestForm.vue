<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowUpIcon } from '@lucide/vue'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from '@/components/ui/input-group'
import { Kbd, KbdGroup } from '@/components/ui/kbd'
import { Spinner } from '@/components/ui/spinner'
import { isApplePlatform } from '@/lib/platform'
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

const modifier = isApplePlatform()
  ? { key: '⌘', spoken: 'Comando' }
  : { key: 'Ctrl', spoken: 'Control' }

// Enter adds a new line; Ctrl+Enter or Cmd+Enter submits.
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    void store.submit()
  }
}

const field = ref<{ $el: HTMLTextAreaElement }>()

defineExpose({ focus: () => field.value?.$el.focus() })
</script>

<template>
  <form class="flex flex-col gap-2" novalidate @submit.prevent="store.submit()">
    <label for="research-question" class="text-sm font-medium text-muted-foreground">
      Pregunta sobre el acceso a la vivienda en España
    </label>

    <InputGroup class="rounded-xl bg-card shadow-sm">
      <InputGroupTextarea
        id="research-question"
        ref="field"
        v-model="store.question"
        rows="3"
        placeholder="Por ejemplo: ¿cuánto ha subido el alquiler en mi ciudad?"
        class="max-h-64 min-h-24 overflow-y-auto px-4 pt-3 text-base"
        :aria-invalid="store.status === 'invalid' ? 'true' : undefined"
        :aria-describedby="store.status === 'invalid' ? 'research-status' : undefined"
        @keydown="onKeydown"
      />
      <InputGroupAddon align="block-end" class="px-3 pb-3">
        <span class="sr-only">Para enviar, pulsa {{ modifier.spoken }} más Intro.</span>
        <KbdGroup aria-hidden="true" data-testid="submit-shortcut">
          <Kbd>{{ modifier.key }}</Kbd>
          <Kbd>↵</Kbd>
        </KbdGroup>
        <InputGroupButton
          type="submit"
          variant="default"
          size="icon-sm"
          class="ml-auto rounded-full"
          aria-label="Enviar"
          :disabled="!store.canSubmit"
          :aria-busy="store.isSubmitting"
        >
          <Spinner v-if="store.isSubmitting" />
          <ArrowUpIcon v-else aria-hidden="true" />
        </InputGroupButton>
      </InputGroupAddon>
    </InputGroup>

    <p
      id="research-status"
      aria-live="polite"
      class="min-h-5 text-sm"
      :class="isError ? 'text-destructive' : 'text-muted-foreground'"
    >
      {{ statusMessage }}
    </p>
  </form>
</template>
