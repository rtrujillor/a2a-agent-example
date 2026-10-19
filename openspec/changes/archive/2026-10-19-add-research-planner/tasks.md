# Tasks

## 1. Domain and retrieval contract

- [x] 1.1 Add the following to `domain/`, as described in design.md (3):
  - in `enums.py`: `ToolName` (`web_search`), `SourceKind` (official, media,
    market), `SourceType` (official, media, market, other), and `Freshness`
    (past_week, past_month, past_year)
  - in `models.py`: `ModelPlanStep`, `ModelPlan`, `PlanStep`, and
    `ResearchPlan`
  - in `errors.py`: `PlanningError`

  Verify with new cases in `tests/unit/test_domain.py`:
  - `ModelPlanStep` accepts an unknown tool string
  - extra fields are rejected
  - an invalid freshness value fails validation
- [x] 1.2 Add to `tools/base.py`:
  - the `SearchTool` protocol (`name`, `async run(SearchQuery) ->
    list[SourceResult]`)
  - `SearchQuery` (query, language, freshness, sites, max results)
  - `SourceResult` (URL, title, publisher, publication date or none,
    retrieval date, source type, snippet)

  Nothing in `tools/` may import LangGraph or the model provider. Verify
  with `tests/unit/tools/test_base.py`: a fake tool satisfies the protocol,
  and a result without a URL or retrieval date fails validation.
- [x] 1.3 Add `tools/catalog.py`, as described in design.md (6):
  - `ToolCatalog` and `DEFAULT_CATALOG`
  - the official allowlists by topic
  - `MARKET_DOMAINS` and `MEDIA_DOMAINS`, choosing their members now (design
    Open Questions)
  - `domain_allowed()` with subdomain matching
  - `source_type_for(url)`

  Verify with `tests/unit/tools/test_catalog.py`:
  - `www.ine.es` is official, and `fakeine.es` is not
  - a market domain is market, and an unknown domain is other
  - a non-HTTP or unparsable URL is other
  - protests and other topics have no allowlist
  - every allowlisted domain is lower-case and has no scheme

## 2. Planner node

- [x] 2.1 Add `plan`, `planner_iterations`, and `searches_used` to `state.py`.
  Add `PLANNER_SYSTEM` and `render_planning_request(classification, budget,
  catalog)` to `prompts.py`, as described in design.md (4). Verify with
  cases in `tests/unit/test_prompts.py`:
  - the request holds a delimited, escaped `<classification>` block and a
    `<limits>` block with the budget, the tool names, and the topic's
    domains
  - it holds no user turn text
  - the reframed question appears when set
- [x] 2.2 Implement `plan_budget()` and `enforce_plan()` in
  `workflow/planner.py`, as described in design.md (3, 5). Verify with
  `tests/unit/workflow/test_planner.py`:
  - the defaults give 4 steps, and 2 searches with 2 iterations give 1 step
  - 0 iterations allow the whole budget
  - unknown tools, empty queries, and off-list sites are dropped
  - `www.` is stripped, and domains are compared case-insensitively
  - a restricted media step becomes official
  - an official step without sites gets the whole allowlist, or is dropped
    without one
  - truncation keeps the model's order
  - an official step beyond the budget is swapped in
  - a plan with no official step for a topic with an allowlist returns
    `None`, and an empty result returns `None`
  - a topic without an allowlist and with no official step is valid
- [x] 2.3 Implement `make_planner(model, settings, catalog, sleep)`:
  - one structured call per attempt
  - invalid output or a `None` plan is retried `1 + http_max_retries` times
    with the classifier's backoff
  - when the attempts run out, raise `PlanningError`
  - provider errors raise `ModelUnavailableError`
  - log without the query text above DEBUG

  Verify with cases in `test_planner.py`, using `FakeStructuredChatModel`:
  - a valid plan is returned with `planner_iterations` set to 1
  - an invalid plan followed by a valid one succeeds
  - all attempts invalid raise `PlanningError`
  - a provider error raises `ModelUnavailableError`
  - an intent with injected instructions that asks for 20 steps on any site
    still yields at most the budget and only allowlisted sites
  - for a reframed personal-advice request, the model's messages contain the
    reframed question and not the original turn

## 3. Graph, executor, and messages

- [x] 3.1 Update `build_graph(classify, plan, checkpointer)` with the
  conditional edge from design.md (1), and wire `make_planner` in
  `server.py`. Verify with `tests/unit/test_graph.py`:
  - an in-scope request reaches the plan node
  - ambiguous and out-of-scope requests end without calling it (the fake
    model's script holds only the classification)
- [x] 3.2 In `a2a/messages.py`:
  - add `plan_summary(plan, language)` with the es/en source-kind labels and
    singular/plural counts from design.md (7)
  - update the `NOT_AVAILABLE` texts

  Verify with cases in `tests/unit/a2a/test_messages.py`:
  - a Spanish summary with four steps
  - an English summary with one step
  - market steps are labelled as offer prices
  - no query or domain appears in the summary
- [x] 3.3 Update `a2a/executor.py`, as described in design.md (2):
  - report the interpretation when an in-scope classification first appears
    in the stream, and the plan when a plan first appears
  - reset `plan`, `planner_iterations`, and `searches_used` in new and
    continued inputs
  - map `PlanningError` to the fixed failure message

  Verify with cases in `tests/unit/a2a/test_executor.py`:
  - an in-scope request gives interpretation, plan, then completed
  - a planning failure gives interpretation, then failed, with no plan update
  - a continued task does not report an earlier plan
- [x] 3.4 Update `tests/integration/a2a/test_server.py` to script the
  classification and then the plan. Verify:
  - the in-scope stream order is task, working, interpretation, plan, and
    completed with the new note
  - ambiguous and out-of-scope streams have no plan update
  - an invalid plan on every attempt ends as failed with the fixed message

  Update `tests/integration/test_live_classifier.py`, or add a live planner
  test marked `live`, so that a real model produces a valid plan for a rents
  question. It stays skipped by default.

## 4. Documentation

- [x] 4.1 Update `README.md`:
  - status: the agent now plans research, and search isn't available yet
  - how `MAX_SEARCHES_PER_REQUEST` and `MAX_PLANNER_ITERATIONS` set the first
    plan's budget

  Verify that the documented defaults match `config.py`. Confirm that
  `docs/architecture/` needs no change (design.md, Context and Decision 1).

## 5. Final checks

- [x] 5.1 Run `uv run --extra dev pytest` at the root, and `pnpm test:unit
  --run`, `pnpm lint`, and `pnpm build` in `web/` (the web client is
  unchanged), and confirm that all pass. Report any check that can't run.
- [ ] 5.2 With the agent (`MODEL_REASONING_EFFORT=none`) and `pnpm dev`
  running, check in the browser:
  - a rents question in Bilbao shows the interpretation, then a plan with at
    least one official step, then the completion note
  - an English question shows an English plan summary
  - a football question shows the rejection with no plan
- [x] 5.3 Run `openspec validate add-research-planner --strict` and confirm
  that it passes.
