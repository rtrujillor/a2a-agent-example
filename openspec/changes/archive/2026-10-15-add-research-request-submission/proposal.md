# Proposal

## Why

The web client shows a static home page, but users can't ask anything yet.
"Submit housing research request" is the first client use case in
`docs/architecture/use-cases.drawio`. The other two client use cases ("Receive
progress or errors" and "Review answer, citations, and limitations") both
start from a submitted task, so this one comes first.

## What Changes

- Add a research request form to the home page, below the existing intro: a
  labeled free-text field and a submit button, with Spanish copy.
- Validate the question before sending it: it must not be empty, and it must
  not exceed a client-side length cap.
- Discover the agent through its agent card at the configured agent URL, then
  send the question to the agent's A2A endpoint as a streamed message.
- Treat the submission as accepted once the agent's first stream event arrives.
  Keep the task and context identifiers, and hand the open stream to the next
  use case.
- Show a fixed Spanish error message when the agent is unreachable, the agent
  card is missing or invalid, or the stream ends before the agent responds.
  Never show raw SDK errors or stack traces.
- Allow one request at a time. Submitting is disabled while a request is
  being sent. A new submission after acceptance replaces the current one.
- Add a research Pinia store, implement the empty A2A service and types
  placeholders, and remove the unused `useResearchTask` composable placeholder.
- Add the shadcn-vue Button and Textarea primitives.

Out of scope:
- Showing progress, answers, citations, or limitations.
- Handling task outcomes after acceptance (rejected, input-required, failed).
- Replying to clarification questions.
- Cancelling a request.
- Persistence and a URL per task.
- Any change to the Python agent.

## Capabilities

### New Capabilities
- `research-request`: How a user writes, validates, and sends a housing
  research question from the web client to the agent. The capability ends
  when the agent accepts the request.

### Modified Capabilities

None. The home page keeps its existing content. The form is added below it,
which `web-app-shell` neither requires nor forbids.

## Impact

- **Code:** `web/` only:
  - `src/views/HomeView.vue`
  - new `src/components/ResearchRequestForm.vue`
  - new `src/stores/research.ts`
  - `src/services/a2aClient.ts`
  - `src/types/research.ts`
  - removal of `src/composables/useResearchTask.ts`
  - new `src/components/ui/button/` and `src/components/ui/textarea/`
  - tests in `src/__tests__/`
- **Dependencies:** no new runtime dependency is expected. `@a2a-js/sdk` is
  already installed. The shadcn-vue CLI may add `reka-ui`, which must be
  pinned exactly.
- **Configuration:** uses the existing `VITE_AGENT_URL` in `web/.env.example`.
  It is a public URL, not a secret.
- **Docs:** `web/README.md` (the layout tree's `composables/` and `stores/`
  entries, and the research store).
- **Agent server:** none. Until the agent exists, the request can only be
  tested against faked transports.
