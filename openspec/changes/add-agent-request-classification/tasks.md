# Tasks

## 1. Configuration and domain

- [x] 1.1 Implement `Settings` in `config.py` as described in design.md (8):
  - existing variables, with `SecretStr` for keys
  - comma-separated `cors_allowed_origins`
  - new `max_clarification_rounds: int = 2` (≥ 0)
  - a clear startup error when `MODEL_NAME` is missing

  Add `MAX_CLARIFICATION_ROUNDS=2` to `.env.example`. Verify with
  `tests/unit/test_config.py`, which covers env parsing, the origins list, the
  missing model name, and secrets not appearing in `repr`.
- [x] 1.2 Implement `domain/enums.py`: `Verdict`, `Topic` (the spec's 13
  values), `LocationLevel`, `ResearchDepth`, `Assumption`, `Outcome`.
  Implement `domain/models.py`: `Location`, `Period`, `ModelClassification`,
  and `ClassifiedRequest`, including the validator that makes an `ambiguous`
  verdict without `clarifying_question` invalid. Implement `domain/errors.py`:
  `ClassificationError`, `ModelUnavailableError`. Verify with
  `tests/unit/test_domain.py`, which covers valid parsing, the
  ambiguous-without-question rejection, an unknown topic rejection, and that
  no I/O imports are needed.

## 2. Classifier node

- [x] 2.1 Add `CLASSIFIER_SYSTEM` and `render_user_turns(turns)` to
  `prompts.py`, as described in design.md (7). Verify with
  `tests/unit/test_prompts.py`, which covers numbered turns inside
  `<user_messages>`, escaping of `&`, `<`, and `>` (a turn containing
  `</user_messages>` can't close the block), and that the system prompt states
  the data-not-instructions rule.
- [x] 2.2 Add `tests/fakes.py` with `FakeStructuredChatModel`: scripted
  results or exceptions per call, and a record of the messages it received.
  Verify with one self-test that scripted results come back in order.
- [x] 2.3 Implement `make_classifier(model, settings)` in
  `workflow/classifier.py`:
  - structured output with `method="json_schema"`
  - bounded validation retries with backoff
  - wrapping of provider and transport errors in `ModelUnavailableError`
  - defaults and assumption codes
  - the outcome and clarification-round table from design.md (2, 3)

  The module must import no `a2a` code. Verify with
  `tests/unit/workflow/test_classifier.py`, which covers:
  - a fully specified question
  - no place and no date (Spain and latest data, with both assumptions)
  - unspecified level
  - a reframed advice question (`NO_PERSONAL_ADVICE`)
  - out of scope
  - ambiguous at rounds 0 and 1 (asks), and at rounds 2 with max 2
    (exhausted)
  - an invalid result followed by a valid one (succeeds)
  - invalid results until the retries run out (`ClassificationError`)
  - a provider exception (`ModelUnavailableError`)
  - all turns sent inside the delimited block
  - an injected "allow ten questions" text, which leaves the bound unchanged

## 3. State and graph

- [x] 3.1 Implement `ResearchState` in `state.py`, and `build_graph(classify,
  checkpointer)` in `graph.py` (`START → classify → END`, compiled once).
  Verify with `tests/unit/test_graph.py`, using the fake model and an
  `InMemorySaver`:
  - two invocations on the same `thread_id` accumulate `user_turns` and
    rounds
  - an `Overwrite` input on that thread starts with only the new turn and 0
    rounds
  - different thread IDs never share turns

## 4. A2A interface

- [x] 4.1 Implement `a2a/messages.py`:
  - fixed Spanish and English texts: intake errors, not available yet, scope
    hint, rephrase, failure
  - topic and assumption labels
  - `interpretation(classified)`, which lists the topic, location, period,
    reframed question, and every assumption
  - English for `"en"`, Spanish otherwise

  Verify with `tests/unit/a2a/test_messages.py`, which covers both languages,
  the fallback for `"ca"`, and that every `Topic` and `Assumption` has a label
  in both languages.
- [x] 4.2 Implement `build_agent_card(settings)` in `a2a/agent_card.py` as
  described in design.md (8). Verify with `tests/unit/a2a/test_agent_card.py`:
  the card has its fields, one skill, streaming, the JSON-RPC interface URL
  from settings, and text modes, and no configured secret value appears in
  the serialized card.
- [x] 4.3 Implement `HousingAgentExecutor(graph, settings)` in
  `a2a/executor.py`:
  - intake guards
  - task creation
  - `start_work` with no text
  - input selection (append vs. `Overwrite`)
  - the request timeout
  - the mapping from outcome to state and message
  - the error mapping with operator logging only
  - `cancel()`

  It must not import the model or tools. Verify with
  `tests/unit/a2a/test_executor.py`, using a stub graph and a recording event
  queue. It covers:
  - each outcome's task state and message
  - English vs. Spanish texts
  - each intake-guard rejection without calling the graph
  - a continuation passing an append input
  - a new task passing `Overwrite`
  - a timeout, a `ClassificationError`, a `ModelUnavailableError`, and an
    unexpected exception, each giving `failed` with the fixed text and no
    exception text

## 5. Server, observability, and integration

- [x] 5.1 Implement `observability.py`: `get_logger()` at `LOG_LEVEL`, and
  `langfuse_callbacks(settings)`, which returns `[]` unless both keys are set.
  The executor passes the callbacks in the run config, and log lines never
  include the question text. Verify with `tests/unit/test_observability.py`:
  no keys gives `[]`, and creating the logger needs no network.
- [x] 5.2 Implement `server.py`:
  - `create_app(settings, model)` builds the graph, executor, handler
    (`InMemoryTaskStore`), card and JSON-RPC routes, and `CORSMiddleware` with
    the configured origins
  - `build_chat_model(settings)`, as described in design.md (6)
  - `main()` runs uvicorn on `A2A_HOST:A2A_PORT`

  Add the `housing-access-agent` console script to `pyproject.toml`. Verify
  that `python -m housing_access_agent.server` starts and serves
  `/.well-known/agent-card.json` on `127.0.0.1:8000` (no model call needed).
- [x] 5.3 Add `tests/integration/a2a/test_server.py`, which uses `create_app`
  with the fake model through `httpx.ASGITransport` and parses the SSE
  stream. It covers:
  - the card at the well-known path
  - a CORS preflight allowed for the configured origin and not for another,
    never `*`
  - in scope: task → working → interpretation → completed
  - out of scope: rejected
  - ambiguous: input-required, then a reply on the same task and context gives
    completed, with the fake model receiving both turns
  - the clarification limit: rejected
  - empty IDs: new IDs per request
  - too long, multi-part, and empty messages: rejected without a model call
  - the request timeout and a model error: failed with no technical detail

  Verify that `pytest` passes with no network access.
- [x] 5.4 Register the `live` marker in `pyproject.toml` (`addopts = "-m 'not
  live'"`). Add `tests/integration/test_live_classifier.py`, which classifies
  the spec's sample questions, including both injection examples, against the
  configured model. Verify that `pytest` reports it deselected by default, and
  that `pytest -m live` runs it when LM Studio is up.
- [x] 5.5 Update `README.md`:
  - the status line
  - the command to start the agent (replacing "will be documented once")
  - `MAX_CLARIFICATION_ROUNDS` in the configuration table
  - the requirement for a model with JSON-schema structured output
  - how to run the `live` tests

  Verify that the documented start command works as written.

- [ ] 5.6 Add the optional `MODEL_REASONING_EFFORT` setting (empty by
  default) and pass it as `reasoning_effort` in `build_chat_model` only when it
  is set, as described in design.md (6, Reasoning models). Add it to
  `.env.example` and the README configuration table. Verify with
  `tests/unit/test_chat_model.py`: the parameter is absent when empty and present
  when set. Also verify that `pytest -m live` passes against LM Studio with
  `MODEL_REASONING_EFFORT=none`.

## 6. Final checks

- [ ] 6.1 Run `pytest` and confirm all tests pass with `live` deselected.
  Run `pnpm test:unit --run`, `pnpm lint`, and `pnpm build` in `web/`, and
  confirm they still pass, since the web client is unchanged. Report any check
  that can't run.
- [ ] 6.2 With the agent and `pnpm dev` running, submit a question from the
  web client. Confirm the client shows "sent" (the first event is accepted
  across CORS), and that the agent log shows the task's outcome without the
  question text.
- [x] 6.3 Run `openspec validate add-agent-request-classification --strict`
  and confirm it passes.

## Workflow follow-up

- Archive the change after review, which creates the `agent-interface` and
  `request-classification` main specs.
- Plan the client change for progress and outcome display, and for replying
  to `input-required` on the same task.
- Optionally fix the model and telemetry labels in `use-cases.drawio`.
