<script setup lang="ts">
import { computed, type Component } from 'vue'
import {
  ArrowUpIcon,
  CircleCheckIcon,
  InfoIcon,
  MessageCircleQuestionIcon,
  TriangleAlertIcon,
  UnplugIcon,
} from '@lucide/vue'
import { Alert, AlertDescription, AlertTitle, type AlertVariants } from '@/components/ui/alert'
import { Card, CardContent } from '@/components/ui/card'
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
import { MAX_QUESTION_LENGTH, type Outcome, type ProgressStep } from '@/types/research'

const store = useResearchStore()

const outcomes: Record<
  Outcome,
  { title: string; icon: Component; variant: AlertVariants['variant']; fallback: string }
> = {
  completed: {
    title: 'Solicitud completada',
    icon: CircleCheckIcon,
    variant: 'default',
    fallback: 'El agente ha terminado.',
  },
  inputRequired: {
    title: 'El agente necesita una aclaración',
    icon: MessageCircleQuestionIcon,
    variant: 'question',
    fallback: '¿Puedes concretar tu pregunta?',
  },
  rejected: {
    title: 'No se puede investigar esta pregunta',
    icon: InfoIcon,
    variant: 'notice',
    fallback: 'La pregunta queda fuera del alcance del agente.',
  },
  failed: {
    title: 'No se pudo completar la solicitud',
    icon: TriangleAlertIcon,
    variant: 'destructive',
    fallback: 'La solicitud no se pudo completar. Inténtalo de nuevo más tarde.',
  },
}

const lost = {
  title: 'Se perdió la conexión con el agente',
  text: 'Inténtalo de nuevo más tarde.',
}

const replyMessages = {
  empty: 'Escribe una respuesta.',
  tooLong: `La respuesta no puede superar los ${MAX_QUESTION_LENGTH} caracteres.`,
} as const

const replyStatusMessage = computed(() => {
  switch (store.replyStatus) {
    case 'invalid':
      return store.replyError ? replyMessages[store.replyError] : ''
    case 'sending':
      return 'Enviando…'
    case 'unreachable':
      return 'No se pudo conectar con el agente. Inténtalo de nuevo más tarde.'
    default:
      return ''
  }
})

const replyIsError = computed(
  () => store.replyStatus === 'invalid' || store.replyStatus === 'unreachable',
)

// Only the question the agent is waiting on gets a reply field.
const replyStepIndex = computed(() =>
  store.phase === 'inputRequired' ? store.steps.length - 1 : -1,
)

function describe(step: ProgressStep): string {
  switch (step.kind) {
    case 'agent':
      return step.text
    case 'user':
      return `Tu respuesta: ${step.text}`
    case 'outcome':
      return `${outcomes[step.outcome].title}. ${step.text || outcomes[step.outcome].fallback}`
    case 'lost':
      return `${lost.title}. ${lost.text}`
  }
}

// The visible list isn't a live region, so the reply field inside it isn't
// announced as content; this one line announces the newest step instead.
const announcement = computed(() => {
  const latest = store.steps[store.steps.length - 1]
  return latest ? describe(latest) : ''
})

const modifier = isApplePlatform()
  ? { key: '⌘', spoken: 'Comando' }
  : { key: 'Ctrl', spoken: 'Control' }

function onReplyKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    void store.reply()
  }
}
</script>

<template>
  <section
    v-if="store.showProgress"
    aria-label="Progreso de la solicitud"
    class="flex flex-col gap-3"
    data-testid="research-progress"
  >
    <p class="sr-only" aria-live="polite" data-testid="progress-announcement">
      {{ announcement }}
    </p>

    <ol class="flex flex-col gap-3">
      <li v-for="(step, index) in store.steps" :key="index" :data-step="step.kind">
        <Card v-if="step.kind === 'agent'" size="sm">
          <CardContent class="text-sm whitespace-pre-line">{{ step.text }}</CardContent>
        </Card>

        <div
          v-else-if="step.kind === 'user'"
          class="ml-auto flex max-w-md flex-col gap-1 rounded-lg bg-muted px-4 py-3 text-sm"
        >
          <span class="text-xs font-medium text-muted-foreground">Tu respuesta</span>
          <span class="whitespace-pre-line">{{ step.text }}</span>
        </div>

        <Alert
          v-else-if="step.kind === 'outcome'"
          role="group"
          :variant="outcomes[step.outcome].variant"
          :data-outcome="step.outcome"
        >
          <component :is="outcomes[step.outcome].icon" aria-hidden="true" />
          <AlertTitle>{{ outcomes[step.outcome].title }}</AlertTitle>
          <AlertDescription class="flex flex-col gap-3">
            <p class="whitespace-pre-line">{{ step.text || outcomes[step.outcome].fallback }}</p>

            <form
              v-if="index === replyStepIndex"
              class="flex flex-col gap-2"
              novalidate
              @submit.prevent="store.reply()"
            >
              <label for="research-reply" class="text-sm font-medium text-foreground">
                Tu respuesta a la pregunta del agente
              </label>
              <InputGroup class="rounded-xl bg-card">
                <InputGroupTextarea
                  id="research-reply"
                  v-model="store.replyText"
                  rows="2"
                  class="max-h-48 min-h-16 overflow-y-auto px-4 pt-3 text-base"
                  :aria-invalid="store.replyStatus === 'invalid' ? 'true' : undefined"
                  aria-describedby="research-reply-hint research-reply-status"
                  @keydown="onReplyKeydown"
                />
                <InputGroupAddon align="block-end" class="px-3 pb-3">
                  <span class="sr-only">
                    Para enviar, pulsa {{ modifier.spoken }} más Intro.
                  </span>
                  <KbdGroup aria-hidden="true">
                    <Kbd>{{ modifier.key }}</Kbd>
                    <Kbd>↵</Kbd>
                  </KbdGroup>
                  <InputGroupButton
                    type="submit"
                    variant="default"
                    size="icon-sm"
                    class="ml-auto rounded-full"
                    aria-label="Enviar respuesta"
                    :disabled="store.isReplying"
                    :aria-busy="store.isReplying"
                  >
                    <Spinner v-if="store.isReplying" />
                    <ArrowUpIcon v-else aria-hidden="true" />
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
              <p id="research-reply-hint" class="text-xs text-muted-foreground">
                O escribe una nueva pregunta en el formulario de arriba.
              </p>
              <p
                id="research-reply-status"
                aria-live="polite"
                class="min-h-5 text-sm"
                :class="replyIsError ? 'text-destructive' : 'text-muted-foreground'"
              >
                {{ replyStatusMessage }}
              </p>
            </form>
          </AlertDescription>
        </Alert>

        <Alert v-else role="group" variant="destructive" data-outcome="lost">
          <UnplugIcon aria-hidden="true" />
          <AlertTitle>{{ lost.title }}</AlertTitle>
          <AlertDescription>{{ lost.text }}</AlertDescription>
        </Alert>
      </li>
    </ol>

    <p
      v-if="store.isWorking"
      class="flex items-center gap-2 text-sm text-muted-foreground"
      data-testid="progress-working"
    >
      <Spinner aria-hidden="true" />
      Interpretando la pregunta…
    </p>
  </section>
</template>
