# Design

## Context

Current `web/src`:
- **`services/a2aClient.ts`:** `submitResearch(text)` sends a message with
  empty `taskId`/`contextId` and resolves on the first stream event.
  `toResearchEvent` maps `task` and `statusUpdate` events to `{ kind, taskId,
  contextId, state }` and drops `status.message`. `message` events keep their
  text.
- **`stores/research.ts`:** keeps `first`, `taskId`, and `contextId`, never
  reads `events`, and closes the previous submission on a new submit.
- **`components/ResearchRequestForm.vue`:** shows the status line ("Solicitud
  enviada.", errors) in a polite live region.
- **`components/ui/`:** has `alert` (`default`, `notice`, `destructive`),
  `card`, `spinner`, `input-group`, and `kbd`.

Observed agent behavior (checked against the running agent in process):
- A new request streams `task SUBMITTED` → `WORKING` (no text) → `WORKING`
  with the interpretation → one of `COMPLETED`, `INPUT_REQUIRED`, `REJECTED`,
  `FAILED`, each with text.
- A reply on an `INPUT_REQUIRED` task streams **`statusUpdate WORKING` first,
  with no `task` event**, then the same sequence.
- The agent's stream closes after a final or interrupted state.

Requirements are in `specs/research-progress/spec.md` and
`specs/research-request/spec.md`. Motivation is in proposal.md.

## Goals / Non-Goals

**Goals:**
- Keep the existing layers: the service is the only code that imports
  `@a2a-js/sdk`, components use the store, and the store uses the service.
- Make the progress model a plain list of steps. Later workflow nodes (plan,
  search, validate) and the eventual answer can then add step kinds without
  reshaping the panel.
- Keep every layer testable without a network, using a fake `fetch` for the
  service and a fake service that yields scripted events for the store and
  the components.

**Non-Goals:**
- Artifacts, answers, citations, and Markdown.
- Resubscribing to a task after a page reload. Cancelling a running task.

## Decisions

### 1. Event types carry the agent's text

```ts
export type TaskStateName =
  | 'TASK_STATE_SUBMITTED' | 'TASK_STATE_WORKING' | 'TASK_STATE_INPUT_REQUIRED'
  | 'TASK_STATE_COMPLETED' | 'TASK_STATE_REJECTED' | 'TASK_STATE_FAILED'
  | 'TASK_STATE_CANCELED' | 'TASK_STATE_AUTH_REQUIRED' | string

export type ResearchEvent =
  | { kind: 'task'; taskId; contextId; state: TaskStateName; text: string }
  | { kind: 'status'; taskId; contextId; state: TaskStateName; text: string }
  | { kind: 'artifact'; taskId; contextId }
  | { kind: 'message'; contextId; text: string }
```

`text` joins the text parts of `status.message`, or is `''` when there are
none. A single `messageText(parts)` helper replaces the inline join that the
`message` case uses today.

### 2. Service: one send path, two entry points

```ts
interface A2AService {
  submitResearch(text: string): Promise<ResearchSubmission>       // ids ''
  replyToTask(ids: { taskId: string; contextId: string }, text: string)
    : Promise<ResearchSubmission>                                 // ids kept
}
```

Both call a private `send(text, ids)`, which uses today's logic: the lazy
client, the stream, resolving on the first event, and `AgentUnavailableError`
for every failure before that event. The reply resolves on its first event
too. For a continuation that is a `status` event, which the current code
already maps.

### 3. Store: steps, a phase, and a guarded reader

```ts
type ProgressStep =
  | { kind: 'agent'; text: string }                          // working + text
  | { kind: 'user'; text: string }                           // a sent reply
  | { kind: 'outcome'; outcome: Outcome; text: string }
  | { kind: 'lost' }                                         // stream broke
type Outcome = 'completed' | 'inputRequired' | 'rejected' | 'failed'

type ProgressPhase = 'idle' | 'working' | 'inputRequired' | 'finished'
```

New store state:
- `steps`, `phase`
- `replyText` (draft), `replyStatus`
  (`'idle' | 'invalid' | 'sending' | 'unreachable'`), `replyError`

New derived values: `showProgress` (`steps.length > 0 || phase !== 'idle'`)
and `isWorking` (`phase === 'working'`).

`follow(submission)` handles the accepted event, then loops over the
remaining events:
- **Events with text:**
  - `WORKING` with text adds an `agent` step.
  - `INPUT_REQUIRED`, `COMPLETED`, `REJECTED`, `FAILED` add an `outcome` step
    and set `phase`: `inputRequired` for a question, `finished` otherwise.
  - `CANCELED` and `AUTH_REQUIRED` count as `failed`, since the agent never
    sends them today. The store keeps the agent's text as-is, and the
    component shows a fixed failure text when it is empty.
  - A `message` event adds an `agent` step.
- **Events without text:** `SUBMITTED`, or `WORKING` with no text, set
  `phase = 'working'` and add no step. `artifact` events are ignored for now.
- **End of stream:** when the loop ends or throws before `phase` leaves
  `working`, a `lost` step is added and `phase` becomes `finished`.

The loop runs without being awaited by `submit()`. `submit()` still returns
on acceptance, so the existing acceptance behavior and its tests keep
working.

Each `follow` call gets a generation number. A new `submit()` or `reset()`
increments it, clears `steps`, and closes the old submission. A loop from an
older generation stops writing as soon as its generation is stale, so a
closed stream's late events can't leak into a new panel.

`reply()`:
1. Validates with the shared `validate()` (empty, too long), using the
   trimmed text.
2. Sets `replyStatus = 'sending'` and calls `replyToTask({ taskId, contextId
   }, text)`.
3. On `AgentUnavailableError`: `replyStatus = 'unreachable'`, the draft is
   kept, and `phase` stays `inputRequired`.
4. On acceptance: adds a `user` step, clears the draft, sets `phase =
   'working'`, and calls `follow()` with the same generation. The earlier
   steps stay.

A second `reply()` while `sending` is ignored.

Validation messages for the reply live in the component, like the form's
messages.

### 4. Component: `ResearchProgress.vue`

```
<section aria-label="Progreso de la solicitud" v-if="store.showProgress">
  <p class="sr-only" aria-live="polite">{{ announcement }}</p>   (latest step)
  <ol>
    agent step   -> Card, text in whitespace-pre-line
    user step    -> "Tu respuesta" + text, muted, aligned as the user's turn
    outcome      -> Alert with icon + AlertTitle + AlertDescription(pre-line)
       completed      variant default      CircleCheck   "Solicitud completada"
       inputRequired  variant question     MessageCircleQuestion
                                                    "El agente necesita una aclaración"
       rejected       variant notice       Info     "No se puede investigar esta pregunta"
       failed         variant destructive  TriangleAlert
                                                    "No se pudo completar la solicitud"
    lost         -> Alert destructive, fixed text
                    "Se perdió la conexión con el agente. Inténtalo de nuevo más tarde."
  </ol>
  <p v-if="isWorking"> <Spinner/> Interpretando la pregunta… </p>
  reply form, inside the last inputRequired block:
    label "Tu respuesta a la pregunta del agente", InputGroupTextarea,
    send button (aria-label "Enviar respuesta", busy while sending),
    hint "O escribe una nueva pregunta en el formulario de arriba.",
    validation and unreachable messages next to the field
</section>
```

- **Live region:** one visually hidden polite region announces the newest
  step's heading and text. The visible list itself isn't a live region, so
  the reply field can sit inside the question block without being announced
  as content. Focus never moves.
- **Plain text only:** text goes through `{{ }}` interpolation with
  `whitespace-pre-line`, never `v-html`.
- **Styling:** the prominent but non-error question uses a new `question`
  CVA variant in `ui/alert` (primary-tinted border and icon), not one-off
  classes.
- **Alert role:** `Alert.vue` renders `role="alert"`, which screen readers
  announce assertively. Inside the panel, each Alert gets `role="group"`
  (fallthrough attributes override it), so only the polite announcer
  speaks.
- **Keyboard:** the reply field takes Ctrl/Cmd+Enter to send, the same as
  the form. Enter adds a line.
- **Where it mounts:** `HomeView.vue`, between `ResearchRequestForm` and
  `ExampleQuestions`.

### 5. The form's status line

"Solicitud enviada." stays, because `research-request` requires it. The panel
is a separate live region that announces steps, not submission status, so the
two never repeat each other.

## Risks / Trade-offs

- [Two polite live regions could queue announcements] → The form line
  changes only at submission, and the panel announces only the newest step,
  so they rarely fire together.
- [The reader loop isn't awaited, so errors could become unhandled] → The
  loop catches everything and turns it into a `lost` step. Store tests wait
  on the loop through a test-only promise from `follow()`.
- [`CANCELED`/`AUTH_REQUIRED` shown as failed] → The agent never sends them
  today. The mapping sits in one function and can change later.
- [Later agent steps (plan, search) will arrive as more `WORKING` texts] →
  They render as `agent` steps with no client change. The spinner label
  "Interpretando la pregunta…" may then need a generic wording. That can wait
  until there are later steps.

## Migration Plan

Client only, and backwards compatible with the agent: an agent that sends
`WORKING` without text still produces a working indicator and an outcome. To
roll back, revert the change.
