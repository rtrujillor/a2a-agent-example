# Tasks

## 1. Primitives and cleanup

- [x] 1.1 Add Button and Textarea with `pnpm dlx shadcn-vue@2.8.2 add button textarea`. Pin any added dependency (for example `reka-ui`) exactly and run `pnpm install`. Replace raw values with token utilities. Verify `pnpm lint` (including `lint:tokens`) passes and no npm/yarn lockfile appeared.
- [x] 1.2 Delete `src/composables/useResearchTask.ts` (and the folder if it is empty). Verify `pnpm type-check` passes and `grep -r useResearchTask src` finds nothing.

## 2. Types and A2A service

- [x] 2.1 Implement `src/types/research.ts` as described in design.md: `MAX_QUESTION_LENGTH = 2000` (with a comment pointing at the future server limit), `SubmissionStatus`, `ValidationError`, `ResearchEvent`, `ResearchSubmission`. Verify `pnpm type-check` passes.
- [x] 2.2 Check the `@a2a-js/sdk` 1.3.0 typings for how to inject `fetchImpl` into the card resolver and the JSON-RPC transport (`ClientFactoryOptions.createFrom`). Record the option names used as a note under this task. Verify with a type-checked call in 2.3.
  - Note: `DefaultAgentCardResolver({ fetchImpl })` for the card, and `JsonRpcTransportFactory({ fetchImpl })` and `RestTransportFactory({ fetchImpl })` for requests, merged with `ClientFactoryOptions.createFrom(ClientFactoryOptions.default, { transports, cardResolver })`. Transports merge by protocol name. If the card does not advertise `capabilities.streaming`, the SDK's `Client.sendMessageStream` falls back to a blocking `SendMessage` and yields its result as one event. That still meets acceptance on the first event.
- [x] 2.3 Implement `createA2AService({ agentUrl, fetchImpl })` and the default `a2aService` in `src/services/a2aClient.ts`:
  - a lazy cached client from `createFromUrl`, dropped after a failure
  - `submitResearch(text)` sends one `ROLE_USER` text-part message with no task or context id, and resolves on the first event mapped to `ResearchEvent`
  - `AgentUnavailableError` for card, network and empty-stream failures
  - `close()` returns the generator

  No SDK type may appear in its exports. Verify `pnpm type-check` passes.
- [x] 2.4 Add `src/__tests__/a2aClient.spec.ts` with a fake `fetch` (sample agent card plus a JSON-RPC SSE stream body). Cover:
  - the card is read from `/.well-known/agent-card.json` under `agentUrl`
  - the sent message has one text part, no `taskId`/`contextId`, and no auth header
  - a first `task` event resolves with its ids
  - an invalid card, a rejected `fetch` and an empty stream each throw `AgentUnavailableError`
  - after a failure, the next call reads the card again
  - `close()` ends the generator

  Verify `pnpm test:unit --run` passes with no network access.

## 3. Research store

- [x] 3.1 Implement `useResearchStore` in `src/stores/research.ts` as described in design.md:
  - `question`, `status`, `validationError`, `taskId`, `contextId`
  - a private current submission
  - `isSubmitting`, `canSubmit`, `submit()`, `reset()`

  Verify `pnpm type-check` passes.
- [x] 3.2 Add `src/__tests__/research.store.spec.ts` with `setActivePinia(createPinia())` and `vi.mock('@/services/a2aClient')`. Cover:
  - empty or whitespace input and 2,001 characters give `invalid` with the right `validationError` and no service call
  - exactly 2,000 characters is accepted
  - the text is trimmed before sending
  - success gives `submitted` with ids
  - `AgentUnavailableError` gives `unreachable`, keeps `question` and allows a retry
  - a second `submit()` while submitting makes no second call
  - a submit after acceptance calls the previous `close()` and clears the ids first

  Verify `pnpm test:unit --run` passes.
- [x] 3.3 Update `web/README.md`:
  - in the layout tree, drop `composables/`, describe `stores/` as holding `research.ts`, and add `components/ResearchRequestForm.vue`
  - add a short "Research request" section: the store states, that `services/a2aClient.ts` is the only SDK importer, and `VITE_AGENT_URL`

  Verify every documented path exists.

## 4. Form and home page

- [x] 4.1 Create `src/components/ResearchRequestForm.vue` using only the store and the Button/Textarea primitives:
  - an `h2` "Haz tu pregunta" and a visible label tied to the textarea
  - `v-model` bound to `store.question`; Enter inserts a newline, Ctrl/Cmd+Enter submits
  - the button is disabled with `aria-busy` while submitting
  - one `aria-live="polite"` status line with the fixed Spanish messages from design.md
  - `aria-invalid` and `aria-describedby` on validation errors
  - `text-destructive` for the connection error

  Use token utilities only. Verify `pnpm lint` passes.
- [x] 4.2 Render `<ResearchRequestForm />` at the end of `src/views/HomeView.vue` without changing its existing content. Verify the existing router and home tests in `src/__tests__/router.spec.ts` still pass.
- [x] 4.3 Add `src/__tests__/ResearchRequestForm.spec.ts` using `mountWithPlugins(HomeView)` with the service mocked. Cover:
  - the form appears below the intro, with its label
  - Enter does not submit, Ctrl+Enter and Cmd+Enter do
  - the empty and too-long messages appear, and the text is kept
  - the busy, disabled button blocks a double click (one service call)
  - "Solicitud enviada." appears on success
  - the fixed connection message appears on `AgentUnavailableError`, with no raw error text, and the button is enabled again
  - the status sits in a polite live region, and focus does not move

  Verify `pnpm test:unit --run` passes.

## 5. Integration check

- [x] 5.1 Run `pnpm test:unit --run`, `pnpm lint` and `pnpm build` in `web/`, and verify all three pass. Then run `pytest` at the repo root and report its result as it is: no agent code changed, and tests may not be configured yet.
  - Note: `pnpm test:unit --run` passes (38 tests in 6 files), and `pnpm lint` and `pnpm build` pass with no warnings. `pytest` is not on the PATH. `.venv/bin/python -m pytest` reports "no tests ran", because `tests/unit/` and `tests/integration/` contain no test files yet. This change touched no agent code.
- [x] 5.2 With `pnpm dev` and no agent running, submit a question in the browser. Verify the request goes to `VITE_AGENT_URL/.well-known/agent-card.json`, the fixed connection message appears with no console stack trace in the UI, and the question stays in the field.
  - Note: checked with headless Chrome over the DevTools protocol, using a separate dev server on port 5199 with `VITE_AGENT_URL=http://127.0.0.1:8000` and nothing listening on 8000. The browser requested `/.well-known/agent-card.json` on 8000. The status read "No se pudo conectar con el agente. Inténtalo de nuevo más tarde." (`text-destructive`). The question stayed in the field, the button was enabled again, the page showed no technical text, and the console had no errors. The browser sent a CORS preflight (`OPTIONS`) because the SDK adds an `A2A-Version` header, so the agent's CORS must allow that header as well as the client origin.

## Workflow follow-up

- Once the Python A2A server exists, run an end-to-end check from the client: card discovery, CORS from the Vite origin (including the `A2A-Version` request header in the preflight), and a first stream event giving "Solicitud enviada.".
- Archive the change after review, so `research-request` becomes a main spec.
