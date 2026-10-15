# Design

## Context

Current `web/src`:
- Pinia and the router are wired in `main.ts`.
- `mountWithPlugins` gives every test a fresh Pinia and a memory-history
  router.
- `HomeView.vue` is static Spanish text.
- `services/a2aClient.ts`, `types/research.ts` and
  `composables/useResearchTask.ts` are empty placeholders (`export {}`).
- `stores/` and `components/ui/` are empty.
- `web/.env.example` already declares `VITE_AGENT_URL=http://127.0.0.1:8000`.

`@a2a-js/sdk` 1.3.0 is installed and provides:
- `ClientFactory.createFromUrl(baseUrl)`, which reads
  `/.well-known/agent-card.json` and picks a transport from the card.
- `client.sendMessageStream(request)`, which returns an
  `AsyncGenerator<StreamResponse>`. `StreamResponse.payload` is a tagged union:
  `task | message | statusUpdate | artifactUpdate`.
- Protobuf-style types: `Role.ROLE_USER`, `Part.content = { $case: 'text', value }`.

The Python agent has no implementation yet, so nothing in this change can run
against a real server. Requirements are in `specs/research-request/spec.md`.
Motivation and scope are in proposal.md.

## Goals / Non-Goals

**Goals:**
- Keep three layers with one job each: the view and component show the form,
  the store owns the submission state, and the service is the only code that
  imports `@a2a-js/sdk`.
- Keep SDK types inside the service. The store and components see only the
  client's own types in `types/research.ts`, so a future SDK change touches
  one file.
- Make every piece testable without a network: the component against a real
  store with a fake service, the store against a fake service, and the
  service against a fake `fetch`.

**Non-Goals:**
- Reading stream events after the first one, or mapping task states to UI.
  That belongs to "Receive progress or errors".
- Multi-turn conversation state, i18n, cancellation, retries.
- Checking whether the card advertises streaming.

## Decisions

### Layout

```
web/src/
+-- views/HomeView.vue               existing intro + <ResearchRequestForm/>
+-- components/
|   +-- ResearchRequestForm.vue      label, Textarea, Button, status/error line
|   +-- ui/button/, ui/textarea/     shadcn-vue CLI primitives
+-- stores/research.ts               useResearchStore
+-- services/a2aClient.ts            createA2AService(), default a2aService
+-- types/research.ts                ResearchEvent, SubmissionStatus, limits
+-- composables/useResearchTask.ts   deleted
```

### Types (`types/research.ts`)

```ts
export const MAX_QUESTION_LENGTH = 2000

export type SubmissionStatus =
  | 'idle' | 'invalid' | 'submitting' | 'submitted' | 'unreachable'

export type ValidationError = 'empty' | 'tooLong'

// Client-side view of one stream event; the SDK shape stays in the service.
export type ResearchEvent =
  | { kind: 'task'; taskId: string; contextId: string; state: string }
  | { kind: 'status'; taskId: string; contextId: string; state: string }
  | { kind: 'artifact'; taskId: string; contextId: string }
  | { kind: 'message'; contextId: string; text: string }

export interface ResearchSubmission {
  events: AsyncIterator<ResearchEvent>   // remaining events, for the next use case
  first: ResearchEvent
  close(): Promise<void>
}
```

- **`state` is a plain string**, the SDK's task-state name. The next change
  gives it a proper union when it maps states to UI. A union written now
  would be guesswork.
- **`MAX_QUESTION_LENGTH` is a client constant.** The agent card has no
  standard field for it. The server will enforce its own cap from config and
  stays the authority.

### Service (`services/a2aClient.ts`)

```ts
export function createA2AService(opts: { agentUrl: string; fetchImpl?: typeof fetch }) {
  // getClient(): lazily ClientFactory.createFromUrl(agentUrl), cached per service
  // submitResearch(text): ResearchSubmission
  //   - builds Message { messageId: crypto.randomUUID(), role: ROLE_USER,
  //       parts: [{ content: { $case: 'text', value: text } }] }, no taskId/contextId
  //   - awaits the first StreamResponse, maps it to ResearchEvent
  //   - stream done before first event -> throws AgentUnavailableError
  //   - any SDK/network/card error   -> throws AgentUnavailableError (cause kept, never shown)
}
export const a2aService = createA2AService({ agentUrl: import.meta.env.VITE_AGENT_URL })
```

- **The service resolves at the first event, not when the request starts.**
  Acceptance is defined by the first event, and an empty stream counts as a
  connection failure (spec). Doing this in the service keeps the store simple.
  Alternative: return the raw generator and let the store wait for the first
  event. Rejected: the store would then have to handle SDK error types.
- **One error type, `AgentUnavailableError`.** The UI shows one fixed message
  for every pre-acceptance failure, so the store doesn't need finer types. The
  original error is kept on its `reason` field for debugging in devtools, but
  it is not logged to any service and not rendered. (`cause` would need
  `ErrorOptions`, which the test tsconfig's `lib: []` does not provide.)
- **Factory plus default instance**, the same pattern as `createAppRouter`.
  Tests build a service with a fake `fetchImpl` and a sample agent card, and
  the store tests replace the default instance with
  `vi.mock('@/services/a2aClient')`.
- **The cached client is dropped after a failure**, so the next submission
  reads the agent card again. Without this, an agent started after the page
  loaded would never be found.
- **The `fetchImpl` reaches the SDK** through the card resolver and the
  JSON-RPC transport factory options (`ClientFactoryOptions.createFrom`). The
  task checks the exact option names against the 1.3.0 typings at apply time.

### Store (`stores/research.ts`)

```
useResearchStore  (setup store)
  state:    question, status: SubmissionStatus, validationError?, taskId?, contextId?
  private:  current?: ResearchSubmission
  getters:  isSubmitting, canSubmit
  actions:  submit(), reset()

submit():
  if status === 'submitting' -> return             (one request at a time)
  text = question.trim(); validate -> 'invalid' + validationError, return
  await current?.close(); clear ids
  status = 'submitting'
  try   { current = await a2aService.submitResearch(text)
          taskId/contextId from current.first; status = 'submitted' }
  catch { status = 'unreachable' }
```

- **`question` lives in the store**, not only in the component, so the text
  survives a failed submission and the next use case can show the submitted
  question.
- **The store keeps the `ResearchSubmission`**, so the stream stays open
  (spec). It isn't exposed as reactive state, because an iterator isn't data.
  The follow-up change adds an action that reads `current.events`. Until
  then, the open stream is simply never read.
- **Alternative:** keep the `useResearchTask` composable as the state owner.
  Rejected: AGENTS.md says components use stores and stores call services. A
  composable alongside a store would give the same state two owners.
- **Ids are cleared before each submission**, because every submission starts
  a new context (spec).

### Component and view

- `ResearchRequestForm.vue` uses only the store:
  - `v-model` binds `store.question`.
  - Submit and Ctrl/Cmd+Enter call `store.submit()`.
  - The button is disabled and `aria-busy` while `isSubmitting`.
- **Messages** (all Spanish, fixed strings in the component):

  | Situation | Message |
  | --- | --- |
  | Empty question | "Escribe una pregunta." |
  | Too long | "La pregunta no puede superar los 2000 caracteres." |
  | Sent | "Solicitud enviada." |
  | Unreachable | "No se pudo conectar con el agente. Inténtalo de nuevo más tarde." |

- **The status line is one `aria-live="polite"` region.** Validation errors
  are also linked to the field with `aria-describedby` and `aria-invalid`.
- **The connection error uses the destructive token style.** The design
  system requires it to look different from limitation notices.
- **There is no shadcn Alert primitive yet.** A short status line with
  `text-destructive` is enough for now. Adding Alert just for one line would
  be premature, and it can be adopted when progress display needs it.
- `HomeView.vue` keeps its content and renders `<ResearchRequestForm />` last.
  The page heading stays the only `h1`, and the form gets an `h2` ("Haz tu
  pregunta").

### Primitives

Add Button and Textarea with `pnpm dlx shadcn-vue@2.8.2 add button textarea`.
Then follow the steps in `web/README.md`: pin `reka-ui` exactly if it is
added, and replace any raw values with token utilities so `lint:tokens`
passes.

## Risks / Trade-offs

- [The A2A wire format can't be checked until the agent exists] → The service
  test uses a recorded sample agent card and an SSE stream body in the 1.x
  JSON-RPC shape. The Python server change must add an end-to-end smoke check
  from the client.
- [The SDK's protobuf codec uses `Buffer` for `raw` parts, which browsers
  don't have] → This change sends and maps only text parts, which don't touch
  `Buffer`. The production build check confirms the bundle loads. If a file
  part ever arrives, the next change must handle it.
- [CORS: the browser blocks calls unless the agent allows the Vite origin] →
  The browser reports this as a network error, so it shows the fixed
  connection message. The agent server change must allow the configured
  client origin (AGENTS.md).
- [The client and server length caps can drift apart] → `MAX_QUESTION_LENGTH`
  has a comment pointing at the server setting. Once the server exists, any
  over-limit rejection it returns is a post-acceptance outcome for the next
  use case.
- [An accepted stream is never read until the next change] → It is harmless
  locally because there is no agent yet. `close()` is called on replace, so
  replaced streams don't leak.
