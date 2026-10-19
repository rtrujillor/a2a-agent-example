# Proposal

## Why

The agent now interprets each question and reports it on the A2A stream: its
reading, a clarifying question, a rejection with a reason, or a failure. The
web client still stops at "Solicitud enviada.", because it reads only the
first stream event. Users never see what the agent understood or why a request
was refused, and a clarifying question is a dead end.
"Receive progress or errors" is the next client use case in
`docs/architecture/use-cases.drawio`.

## What Changes

- Read the stream after the agent accepts a request, and show each step in a
  panel under the form on the home page:
  - progress while the agent works
  - the agent's interpretation and its assumptions
  - the final outcome: completed, a clarifying question, rejected, or failed
- Show the agent's messages as plain text with line breaks kept. Never render
  them as HTML.
- Give each outcome its own look:
  - neutral for completed
  - prominent but not an error for a clarifying question
  - a notice for rejected, since the user did nothing wrong
  - an error for failed
- Show a fixed Spanish error when the stream breaks before the agent reaches
  a final or interrupted state.
- Let the user answer a clarifying question in a field inside that question's
  block. The answer is sent on the same task and context, so the agent
  interprets both messages together. The exchange stays visible: the user's
  reply appears, then the agent's next steps.
- Keep the main form for new questions only. Submitting it clears the panel,
  closes the open stream, and starts a fresh request.
- Announce new steps to assistive technology without moving focus.
- Fix the stale home-page title expected by `router.spec.ts`. The current
  title came from a later edit, and the check fails today. The `web/` test
  suite must pass for this change.

Out of scope:
- Rendering a research answer, citations, limitations, or artifacts. The
  agent doesn't produce them yet.
- Markdown rendering.
- A page or URL for each request, persistence, and cancelling a running task.
- Agent changes.

## Capabilities

### New Capabilities
- `research-progress`: How the web client shows an accepted request's
  progress, interpretation, and outcome, including errors and a broken
  stream, and how the user answers the agent's clarifying question.

### Modified Capabilities
- `research-request`: "Streamed submission" says every submission starts a
  fresh request with no task or context identifier. That stays true for the
  main form. A reply to a clarifying question is a separate kind of message
  that carries the identifiers of the task it answers.

## Impact

- **Code:** `web/src/` only:
  - `services/a2aClient.ts`: keep the status message text, and add a reply
    that reuses the task and context identifiers
  - `types/research.ts`: event text and progress step types
  - `stores/research.ts`: consume events after acceptance, keep the steps,
    and add `reply()`
  - new `components/ResearchProgress.vue`
  - `views/HomeView.vue`
  - tests in `src/__tests__/`, including the `router.spec.ts` title fix
- **Dependencies:** none. It uses the existing Alert (`default`, `notice`,
  `destructive`), Card, Spinner, and InputGroup primitives.
- **Agent:** no change. Continuation streams already start with a status
  update, which counts as acceptance.
- **Docs:** `web/README.md` (the research store and the new component).
