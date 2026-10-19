# Tasks

## 1. Baseline

- [x] 1.1 Update the stale title assertion in `src/__tests__/router.spec.ts`
  to the current home-page heading ("Problema de acceso a la vivienda en
  España"). Verify that `pnpm test:unit --run` passes before any other
  change.

## 2. Types and service

- [x] 2.1 Extend `src/types/research.ts` as described in design.md (1):
  - `TaskStateName`
  - `text` on `task` and `status` events
  - `ProgressStep`, `Outcome`, `ProgressPhase`, `ReplyStatus`

  Verify that `pnpm type-check` passes.
- [x] 2.2 In `src/services/a2aClient.ts`:
  - map `status.message` text parts into `text` with one `messageText()`
    helper, also used by `message` events
  - add `replyToTask({ taskId, contextId }, text)`, sharing a private
    `send()` with `submitResearch`

  No SDK type may appear in the exports. Verify with new cases in
  `src/__tests__/a2aClient.spec.ts`:
  - a status update's message text is mapped, and a status update without a
    message gives `''`
  - a reply sends one text part with the given `taskId` and `contextId`
  - a reply resolves on a first `statusUpdate` event, with no `task`
  - reply failures before the first event throw `AgentUnavailableError`

## 3. Research store

- [x] 3.1 Implement in `src/stores/research.ts` as described in design.md
  (3):
  - `steps`, `phase`, `replyText`, `replyStatus`, `replyError`,
    `showProgress`, `isWorking`, `isReplying`
  - `follow()` with the generation guard
  - `reply()`
  - `submit()` and `reset()` clearing the steps

  Verify that `pnpm type-check` passes.
- [x] 3.2 Extend `src/__tests__/research.store.spec.ts` with a fake service
  that yields scripted events. Cover:
  - `WORKING` without text sets `working` and adds no step
  - `WORKING` with text adds an `agent` step
  - each outcome state adds the matching `outcome` step and phase
  - `CANCELED` maps to `failed`
  - a stream that ends or throws while working adds `lost`
  - a new `submit()` clears the steps, closes the old stream, and ignores
    the old stream's late events
  - `reply()`:
    - an empty or too-long reply is `invalid` with no service call
    - a valid reply calls `replyToTask` with the trimmed text and the
      store's IDs, adds a `user` step, and keeps the earlier steps
    - a second reply while sending is ignored
    - `AgentUnavailableError` keeps the draft and sets `unreachable`

  Verify that `pnpm test:unit --run` passes.

## 4. Progress panel

- [x] 4.1 Add `src/components/ResearchProgress.vue` as described in design.md
  (4), and mount it in `src/views/HomeView.vue` between the form and the
  example questions. Use only `ui/` primitives and token utilities. If the
  question block needs a new look, add it as a CVA variant in `ui/alert`.
  Verify that `pnpm lint` (including `lint:tokens`) passes.
- [x] 4.2 Add `src/__tests__/ResearchProgress.spec.ts` with a real store and a
  mocked service. Cover:
  - hidden before a request
  - the working indicator and its Spanish text
  - an agent step with line breaks kept, and `<b>` shown literally
  - each outcome's heading and style variant
  - the lost-connection error with earlier steps kept
  - the reply field: label, accessible name, hint, Ctrl/Cmd+Enter, the
    empty-reply message, busy and disabled while sending
  - after a reply, the user step appears and the field is gone
  - a second clarifying question shows a new reply field
  - the polite announcement holds the newest step, and focus doesn't move

  Extend `src/__tests__/HomeView.spec.ts` to check that the panel sits
  between the form and the examples. Verify that `pnpm test:unit --run`
  passes.
- [x] 4.3 Update `web/README.md`: the research store's progress state and
  `reply()`, and `ResearchProgress.vue` in the layout tree. Verify that the
  documented names match the code.

## 5. Final checks

- [x] 5.1 Run `pnpm test:unit --run`, `pnpm lint`, `pnpm type-check`, and
  `pnpm build` in `web/`, and `uv run --extra dev pytest` at the root, and
  confirm all pass. Report any check that can't run.
- [ ] 5.2 With the agent (`MODEL_REASONING_EFFORT=none`) and `pnpm dev`
  running, check in the browser:
  - an in-scope question shows the interpretation, then the completed note
  - "¿Y los precios?" shows a clarifying question, and replying "Alquiler en
    Bilbao" continues to an outcome
  - a football question shows the notice-style rejection
  - stopping the agent mid-request shows the lost-connection error
- [x] 5.3 Run `openspec validate add-research-progress --strict` and confirm
  it passes.

## Workflow follow-up

- Archive after review. Archiving creates the `research-progress` main spec
  and updates "Streamed submission" in `research-request`.
