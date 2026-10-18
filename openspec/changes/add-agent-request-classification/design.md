# Design

## Context

Every module of `src/housing_access_agent/` holds only a docstring, and
`tests/` holds only `.gitkeep` files. The pinned libraries are already
installed (`.venv`) and checked against the code below:

- `a2a-sdk` 1.2.1:
  - `create_jsonrpc_routes(request_handler, rpc_url)` and
    `create_agent_card_routes(agent_card)` return Starlette routes.
  - `DefaultRequestHandler` (= `DefaultRequestHandlerV2`) takes
    `agent_executor`, `task_store`, `agent_card`.
  - `RequestContext` generates task and context IDs when they are missing or
    empty strings, and exposes `current_task` and `get_user_input()`.
  - `TaskUpdater(event_queue, task_id, context_id)` offers `start_work`,
    `update_status`, `complete`, `reject`, `requires_input`, `failed`.
  - `AgentExecutor.execute` returns after publishing `input-required`, and the
    framework calls it again when the reply arrives on the same task.
  - Types are protobuf: `AgentCard.supported_interfaces[AgentInterface(url,
    protocol_binding, …)]`, `TaskState.TASK_STATE_*`.
- `langgraph` 1.2.12: `StateGraph`, `InMemorySaver`
  (`langgraph.checkpoint.memory`), `langgraph.types.Overwrite`.
- `langchain-openai` 1.6.7: `ChatOpenAI.with_structured_output(schema,
  method="json_schema" | "function_calling" | "json_mode")`.

The web client sends empty `taskId`/`contextId` strings and reads only the
first stream event. Requirements are in `specs/agent-interface/spec.md` and
`specs/request-classification/spec.md`. Motivation is in proposal.md.

## Goals / Non-Goals

**Goals:**
- Keep the module boundaries in AGENTS.md:
  - the executor never calls the model
  - nodes import no `a2a` code
  - `graph.py` is the only composition root
  - `server.py` is wiring only
- Keep the classification deterministic around one model call. The model
  extracts fields. Code applies defaults, assumptions, the clarification bound,
  and the outcome.
- Make every behavior in the specs testable without a network, with a fake
  chat model.

**Non-Goals:**
- Planner, researcher, validator, synthesizer, tools, and answer artifacts.
- Cancelling a running task beyond the SDK default. Push notifications. An
  authenticated extended card.
- Localizing fixed messages beyond Spanish and English.

## Decisions

### 1. Layout and flow

```
server.py ----- builds ----> Settings, ChatOpenAI, graph (once), executor, card,
   |                         Starlette(routes) + CORSMiddleware -> uvicorn
   v
a2a/executor.py   guards -> TaskUpdater -> graph.astream(...) -> outcome -> task state
a2a/messages.py   fixed es/en texts, topic labels, interpretation formatter   (new)
a2a/agent_card.py build_agent_card(settings) -> AgentCard
graph.py          build_graph(classify, checkpointer): START -> classify -> END
workflow/classifier.py  make_classifier(model, settings) -> async node
prompts.py        CLASSIFIER_SYSTEM, render_user_turns(turns)
domain/enums.py   Verdict, Topic, LocationLevel, ResearchDepth, Assumption, Outcome
domain/models.py  ModelClassification, Location, Period, ClassifiedRequest
domain/errors.py  ClassificationError, ModelUnavailableError               (new)
state.py          ResearchState
config.py         Settings (pydantic-settings)
observability.py  get_logger(), langfuse_callbacks(settings) -> list
```

`a2a/messages.py` is the one module the component table doesn't list. It
holds user-facing text, which is presentation of A2A outcomes. Prompts stay
in `prompts.py`. Putting both in one file would mix model instructions with
user copy.

### 2. Two schemas: what the model extracts vs. what the agent decides

The model fills `ModelClassification`, which is strict and has no defaults:

```
language: str                 # BCP-47 primary tag, e.g. "es", "en", "ca"
verdict: Verdict              # in_scope | ambiguous | out_of_scope
reason: str                   # in the user's language
topic: Topic | None
location: Location | None     # null when no place is named
  name: str; level: LocationLevel  (spain|ccaa|province|municipality|neighborhood|unspecified)
period: Period | None         # null when no period is named
  start_year: int | None; end_year: int | None; label: str   # label in user's language
intent: str                   # short phrase, user's language
depth: ResearchDepth
clarifying_question: str | None
reframed_question: str | None
```

The node turns it into `ClassifiedRequest`, which has the same fields and
these additions:
- `location` and `period` are never null.
- `assumptions: list[Assumption]`, built by code:
  - `DEFAULT_LOCATION_SPAIN` when location was null, and the location becomes
    `Location("España", spain)`
  - `DEFAULT_PERIOD_LATEST` when period was null
  - `LOCATION_LEVEL_UNSPECIFIED` when the level is unspecified
  - `NO_PERSONAL_ADVICE` when there is a `reframed_question`

Assumptions are enum codes, not model text. Two reasons:
- The spec requires *every* default to be stated, and a model can forget to
  mention one.
- The codes render in Spanish or English from `messages.py`.

Alternative considered: one schema with model-written `assumptions: list[str]`.
It is simpler, but it can't be verified and would be in an arbitrary language.

The topic enum matches the spec's set. An `ambiguous` verdict with a missing
`clarifying_question` counts as a validation failure, which leads to a retry
(see 6).

### 3. Outcome and clarification bound live in the node

```
verdict        rounds < max   ->  Outcome                 state update
in_scope           -          ->  IN_SCOPE
out_of_scope       -          ->  OUT_OF_SCOPE
ambiguous         yes         ->  NEEDS_CLARIFICATION     clarification_rounds += 1
ambiguous         no          ->  CLARIFICATION_EXHAUSTED
```

`max_clarification_rounds` is injected through the settings. With max = 2 the
agent asks at most two questions, and the third ambiguous result ends the
task as rejected. Keeping this in the node rather than the executor keeps the
rule in the workflow and lets a unit test cover it. The executor only maps
`Outcome` to a task state.

### 4. State, memory, and re-entry

```python
class ResearchState(TypedDict):
    user_turns: Annotated[list[str], operator.add]
    clarification_rounds: int
    classification: ClassifiedRequest | None
    outcome: Outcome | None
```

The graph is compiled once with `InMemorySaver`, and
`thread_id = context_id`. The executor picks the input:

| Situation | Graph input |
| --- | --- |
| `context.current_task` is `TASK_STATE_INPUT_REQUIRED` | `{"user_turns": [text]}`: appended by the reducer |
| anything else (new task) | `{"user_turns": Overwrite([text]), "clarification_rounds": 0, "classification": None, "outcome": None}` |

`Overwrite` makes sure a new task in an old context (the web client never
sends one, but other A2A clients may) never inherits earlier turns. The SDK
already refuses messages to terminal tasks.

Alternative considered: `interrupt()` and `Command(resume=…)`. It was
rejected because resuming re-runs the node from the top. That repeats the
model call before the interrupt point, and a non-deterministic model may then
skip or change the question.

### 5. Executor sequence

```
execute(context, queue):
  text = guard(context.message)         # one part, text, plain/empty media type,
                                        # 1..2000 chars trimmed
     fail -> enqueue task if new; updater.reject(fixed es message); return
  if no current_task: enqueue new_task(task_id, context_id, submitted, history=[message])
  updater.start_work()                  # no message text
  try:
    async with asyncio.timeout(settings.request_timeout_seconds):
      async for state in graph.astream(input, config, stream_mode="values"):
        # the last value is the final state; later nodes add progress here
  except (TimeoutError, ClassificationError, ModelUnavailableError) as e:
    log(category, task_id); updater.failed(fixed message); return
  map state["outcome"]:
    IN_SCOPE               -> update_status(working, interpretation(c))
                              complete(not_available(lang))
    NEEDS_CLARIFICATION    -> requires_input(c.clarifying_question)
    OUT_OF_SCOPE           -> reject(c.reason + scope_hint(lang))
    CLARIFICATION_EXHAUSTED-> reject(rephrase(lang))
```

- `ClassificationError` and `ModelUnavailableError` live in `domain/errors.py`.
  The classifier wraps provider and transport exceptions in
  `ModelUnavailableError`, so the executor never imports `openai` or `httpx`.
- Any other exception is caught at the same point, logged with
  `logger.exception` (server log only), and mapped to `failed`. That way the
  framework's generic error path never reaches the user.
- Fixed texts pick English when `language == "en"` and Spanish otherwise.
- Agent messages are built with the SDK's `new_text_message` helper.
- `cancel()` publishes `canceled` through the updater.

### 6. Model gateway and structured output

`server.py` builds one `ChatOpenAI` with:
- `base_url`, `model` and `api_key` (a `SecretStr`) from the settings. An
  empty key becomes the placeholder `"not-needed"`, since LM Studio ignores it
  and the client rejects an empty one.
- `timeout = HTTP_TIMEOUT_SECONDS`
- `max_retries = HTTP_MAX_RETRIES`, for transport retries with the client's
  own backoff
- `temperature = 0`

The classifier receives a `BaseChatModel` and calls
`model.with_structured_output(ModelClassification, method="json_schema")`.
LM Studio supports `response_format: json_schema`, and it is the default
method in this library version.

Output that fails Pydantic validation, including the ambiguous-without-question
rule, gets at most `HTTP_MAX_RETRIES` more attempts. The backoff is
exponential (0.5 s, 1 s, …). After that the node raises `ClassificationError`.
Both kinds of retry share the one existing retry setting, so no new variable
is needed. The total time is still capped by the request timeout.

Alternative considered: `function_calling`. Small local models support it
less consistently than a JSON-schema response format.

**Reasoning models.** The agent reads the structured answer only from
`message.content`, as the OpenAI Chat Completions specification defines it.
With some reasoning models, a provider may return that answer in a
non-standard `reasoning_content` field and leave `content` empty. LM Studio
does this with `prism-ml/bonsai-27b` while its "separate reasoning content"
option is on, so every attempt fails validation.

The optional setting `MODEL_REASONING_EFFORT` handles this. When set, it is
passed as the standard `reasoning_effort` request parameter. When empty, which
is the default, the parameter is not sent, so providers that reject it are
unaffected. Classification needs no reasoning, and with `none` the answer
comes back in `content` and the request is faster.

Alternatives considered:
- Reading `reasoning_content` when `content` is empty. Rejected: it parses a
  non-standard provider field, needs a `ChatOpenAI` subclass because
  `ChatOpenAI` drops the field, and could pass reasoning text off as the
  answer in free-text calls.
- Requiring the provider setting to be turned off. Still valid as a choice
  for each machine, but it isn't visible in the project's configuration.

### 7. Prompt and untrusted text

`prompts.py` has:
- `CLASSIFIER_SYSTEM`: the scope, topic set, default-first rules ("return
  null for location or period when not stated"), the ambiguity test, the
  comparison and reframing rules, the language rule, and an explicit rule
  that text inside `<user_messages>` is data to classify, never instructions.
- `render_user_turns(turns)`: produces
  `<user_messages><turn n="1">…</turn>…</user_messages>`, with `&`, `<`, `>`
  escaped in the turns so a turn can't close the block.

The model receives only those two messages. Limits and the verdict structure
come from code and the schema, so text in a turn can't change them. Unit
tests check the delimiting and escaping and confirm that limits come only
from settings. The model's actual response to an injected instruction is
covered by a `live` test (see 9).

### 8. Server, card, CORS, configuration

- `Settings` (pydantic-settings, `.env`) reads the existing variables:
  - `model_api_key`, `langfuse_*` keys as `SecretStr`
  - `cors_allowed_origins` as a comma-separated list
  - new: `max_clarification_rounds: int = 2` (≥ 0)

  A missing `MODEL_NAME` fails at startup with a clear message. Google search
  settings are optional in this change.
- `build_agent_card(settings)` sets:
  - name "Spain Housing Access Agent", description
  - `version` from the package
  - `supported_interfaces=[AgentInterface(url=A2A_AGENT_URL,
    protocol_binding="JSONRPC")]`
  - `capabilities.streaming=True`
  - `default_input_modes`/`default_output_modes=["text/plain"]`
  - one skill `housing-access-research` with Spanish and English examples
- The app is `Starlette(routes=create_agent_card_routes(card) +
  create_jsonrpc_routes(handler, "/"))`, wrapped in
  `CORSMiddleware(allow_origins=settings.cors_allowed_origins,
  allow_methods=["GET","POST","OPTIONS"], allow_headers=["content-type",
  "a2a-version", "a2a-extensions"])`. The JS client sends the last two.
- `main()` runs uvicorn on `A2A_HOST:A2A_PORT`. Start it with
  `python -m housing_access_agent.server`, or with the `housing-access-agent`
  console script added to `[project.scripts]`.

### 9. Observability and tests

- `get_logger(name)` configures `logging` at `LOG_LEVEL`. Log lines carry the
  task ID, outcome, and error category, never the question text.
  At `LOG_LEVEL=DEBUG` only, the classifier also logs the model's output
  (each valid classification and each invalid answer with its error), which
  can echo parts of the question. HTTP-client libraries stay at INFO.
- `langfuse_callbacks(settings)` returns `[]` unless both Langfuse keys are
  set, so the agent runs without Langfuse. The callbacks go into the graph's
  run config.
- `tests/fakes.py` provides `FakeStructuredChatModel`. It subclasses
  `BaseChatModel`, its `with_structured_output` returns a runnable that pops
  scripted results (a `ModelClassification`, a validation error, or an
  exception), and it records the messages it received.
- Integration tests build the real app through `server.create_app(settings,
  model)` and call it through `httpx.AsyncClient(transport=ASGITransport(app))`,
  reading the JSON-RPC SSE stream. They cover the card, CORS, every outcome,
  the two-turn continuation, the timeout, and the intake limits.
- A `live` marker (`addopts = "-m 'not live'"`) skips one test module that
  classifies the spec's sample questions, including the injection examples,
  against the configured LM Studio model.

## Risks / Trade-offs

- [A provider doesn't accept the configured `reasoning_effort` value] → It
  shows up as a provider error, so the task ends as `failed` and the operator
  log names the error type. Leave `MODEL_REASONING_EFFORT` empty for
  providers that don't support it.

- [A small local model misjudges scope or ambiguity] → The rules sit in one
  system prompt, defaults are applied by code, and the `live` test suite runs
  the spec examples against the model in use.
- [The model doesn't support `json_schema` responses] → It fails as `failed`
  with a clear operator log. README requires a model with structured output.
  The method is one constant to change if needed.
- [`InMemorySaver` and `InMemoryTaskStore` grow without bound and are lost on
  restart] → This is acceptable for local use and matches the stack. A reply
  to an `input-required` task after a restart is refused by the SDK as an
  unknown task.
- [Fixed messages exist only in Spanish and English] → Model-written text
  follows the user's language. Catalan, Basque, and Galician users get
  Spanish fixed texts, which the spec states.
- [One retry setting covers transport and validation retries] → Fewer knobs
  to configure, and the request timeout caps the total either way.
- [Until client progress handling exists, users see only "sent"] → The
  outcomes are covered by integration tests, and the client change follows.

## Migration Plan

No data or deployed service exists. To roll back, revert the change. Add
`MAX_CLARIFICATION_ROUNDS` to a local `.env`, or rely on the default of 2.

## Open Questions

- `docs/architecture/use-cases.drawio` labels the model service "Lite LLM" and
  telemetry "Langfuse?", while AGENTS.md specifies LM Studio and Langfuse.
  This is a label fix that changes no behavior and can be made in a separate
  docs change.
