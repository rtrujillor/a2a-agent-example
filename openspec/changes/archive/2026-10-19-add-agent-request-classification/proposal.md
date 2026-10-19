# Proposal

## Why

The web client can send a research question, but nothing answers it yet:
every module of the Python agent is still an empty placeholder. "Interpret and
classify request" is the first agent use case in
`docs/architecture/use-cases.drawio`, and every later step (plan, retrieve,
validate, synthesize) starts from a classified request. Building it as a
walking skeleton makes the agent reachable over A2A for the first time and
fixes how requests map to task states before more steps are added.

## What Changes

- Serve the agent over A2A on `127.0.0.1`, with an agent card that declares one
  research skill and streaming. Only the configured web origin is allowed by
  CORS.
- Validate each incoming message before any model call: one text part, plain
  text, not empty, at most 2,000 characters. Invalid messages are rejected with
  a clear message.
- Classify each request with the language model into structured fields:
  language, scope verdict, topic, location, period, intent, research depth,
  stated assumptions, and an optional clarifying question or reframed question.
- Apply a default-first ambiguity policy:
  - A missing location defaults to Spain as a whole.
  - A missing period defaults to the latest available data.
  - An unclear location level is left for later steps to resolve.
  - Every default is recorded as an assumption and shown to the user.
  - A request counts as ambiguous only when the topic or intent can't be
    determined.
- Map the verdict to A2A task states:
  - Out of scope ends as `rejected` with an explanation.
  - Ambiguous ends as `input-required` with one clarifying question.
  - In scope reports a "Entendido: …" progress update with the interpretation
    and its assumptions, then ends as `completed` with a message that research
    is not available yet.
- Support replies to `input-required` on the same task. The agent re-classifies
  the whole exchange. When the configured maximum of clarification rounds is
  reached, the request ends as `rejected` and the user is asked to rephrase.
- Treat requests that compare Spain with other countries as in scope. Requests
  for personal advice that have a researchable core are reframed as market
  research instead of being rejected.
- Report model, timeout, and parsing errors as `failed` with a fixed message.
  Never send stack traces or raw provider errors to the user.
- Bound each request by the configured request timeout. Retry model calls a
  bounded number of times.
- Make tracing optional. Langfuse is used only when its keys are configured.
- Add a command to start the agent server, and unit and in-process integration
  tests that need no network.

Out of scope:
- Planning, retrieval, validation, and synthesis, and the real research
  answer, citations, and answer artifacts.
- Web search and official-source tools.
- Web client changes. The client already connects. Showing progress and task
  outcomes, and replying to `input-required`, are later client changes.
- Long-term memory and persistence. Authentication for public deployment.

## Capabilities

### New Capabilities
- `agent-interface`: How the agent publishes itself and handles A2A tasks:
  - the agent card and its skill
  - message intake limits
  - CORS and binding
  - the mapping from workflow outcomes to task states and user-facing messages
  - continuation of `input-required` tasks
  - error handling without technical detail
- `request-classification`: How the agent interprets a housing question: the
  classified fields, the scope rules, the default-first ambiguity policy, the
  stated assumptions, clarification bounds, and the handling of untrusted user
  text.

### Modified Capabilities

None. `research-request` already ends when the agent accepts the request.
Before acceptance, the client behaves the same against the real agent.

## Impact

- **Code:** `src/housing_access_agent/`:
  - `config.py`, `domain/`, `state.py`, `prompts.py`
  - `workflow/classifier.py`
  - `graph.py`, which ends after classification for now
  - `a2a/agent_card.py`, `a2a/executor.py`, `server.py`
  - `observability.py`

  The other workflow and tool modules stay placeholders.
- **Tests:** new `tests/unit/` (classifier, domain, executor mapping) and
  `tests/integration/a2a/` (card, stream, rejected, input-required with
  continuation, failed, limits) using a fake chat model.
- **Configuration:** add `MAX_CLARIFICATION_ROUNDS` to `.env.example`. The
  existing model, A2A, CORS, timeout, retry, and Langfuse variables are used
  as they are.
- **Dependencies:** none expected. `a2a-sdk`, `langgraph`, `langchain-openai`,
  `langfuse`, `pydantic-settings`, and `uvicorn` are already pinned.
- **Docs:** `README.md` (status, the command to start the agent, the new
  variable). The diagrams need no structural change: the Request Classifier,
  Agent Interface, and their flows already exist.
