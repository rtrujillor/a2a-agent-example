# Tasks

## 1. Domain, state, and configuration

- [x] 1.1 Move `SearchQuery` and `SourceResult` from `tools/base.py` to `domain/models.py`, and re-export them from `tools/base.py` (design 2). Add `GapReason` (empty, failed) to `domain/enums.py`, `Evidence` and `SearchGap` to `domain/models.py`, and `SearchErrorCategory` and `SearchToolError` to `tools/base.py` (no `RetrievalError`: see design 3). Verify that `tests/unit/tools/test_base.py` still passes unchanged, and that new cases in `tests/unit/test_domain.py` reject an `Evidence` with a negative step and an unknown gap reason.
- [x] 1.2 Add `research_step`, `evidence`, and `gaps` to `ResearchState` (design 2). Verify with `tests/unit/test_graph.py` once group 3 wires the node.
- [x] 1.3 In `config.py`, replace `google_search_api_key` and `google_search_engine_id` with `brave_search_api_key: SecretStr` and `search_min_interval_seconds: float = 1.0` (`ge=0`). Verify with `tests/unit/test_config.py`: the defaults, a negative interval rejected, and the key hidden in `repr`. Update `tests/unit/a2a/test_agent_card.py` to pass `brave_search_api_key` and keep checking that the key never reaches the card.
- [x] 1.4 Update `.env.example` (`BRAVE_SEARCH_API_KEY=`, `SEARCH_MIN_INTERVAL_SECONDS=1`, no Google variables) and the configuration table and prerequisites in `README.md`. Verify by searching both files for `GOOGLE`, which should find nothing.

## 2. Brave Search adapter

- [x] 2.1 Delete `tools/google_search.py` and add `tools/brave_search.py` with `BraveSearchTool` and `SearchToolError` (with a category), following the request mapping in design 4. The adapter takes an injected `httpx.AsyncClient`, clock, and sleep. Verify with `tests/unit/tools/test_brave_search.py` using `httpx.MockTransport`, with no network:
  - fixed HTTPS host and `X-Subscription-Token` header
  - `country=ES`
  - `count` capped at 20
  - each freshness value
  - one site, and two sites as `(site:a OR site:b)`
  - an unsupported language falling back to `es`
- [x] 2.2 Map the response to `SourceResult` (design 4) and verify with unit tests:
  - `<strong>` and HTML entities removed from title and snippet
  - publisher fallback order: `profile.name`, then `meta_url.hostname`, then the URL host
  - `page_age` becoming a date, and a missing `page_age` giving None
  - `source_type` set from the catalog, with an injected snippet unable to change it
  - a response without `web.results` giving an empty list
- [x] 2.3 Add retries, backoff, `Retry-After` handling (capped at 10 s), and pacing (design 5). Verify with unit tests using a fake sleep and clock:
  - a timeout retried and then succeeding
  - 500 and 429 retried up to `http_max_retries` and then raising `SearchToolError` with the right category
  - 401 and 422 raised without a retry
  - invalid JSON raised as `invalid_response`
  - `Retry-After: 3` waiting at least 3 s
  - two consecutive calls at least `search_min_interval_seconds` apart
  - the key never appearing in log records, checked with `caplog`

## 3. Researcher node and graph

- [x] 3.1 Implement `make_researcher` in `workflow/researcher.py` (design 3): one step per call, with the query built from the step and settings, the tool picked from an injected mapping, and `searches_used` and `research_step` incremented. Verify with `tests/unit/workflow/test_researcher.py` using a fake `SearchTool`: the query fields match the step, results are capped at `max_results_per_search`, and no model is used.
- [x] 3.2 Add the result rules and verify each with a unit test:
  - non-http(s) URLs dropped
  - off-site results dropped for a step with sites, and `www.` subdomains kept
  - URLs deduplicated across steps (host case, trailing slash, fragment) and kept under the first step
  - empty and failed gaps recorded, with the remaining steps still run
  - no evidence left after the last step when every step is a gap (the executor fails the task)
  - a snippet with an injected instruction leaving the plan and search count unchanged
- [x] 3.3 Wire the node in `graph.py` (`plan -> research`, loop while steps remain, then `END`) and pass the researcher into `build_graph`. Verify in `tests/unit/test_graph.py` that a 3-step plan with a fake tool runs 3 searches and ends with evidence, and that an ambiguous request runs none.

## 4. Executor progress and outcomes

- [x] 4.1 Add `search_update` and `sources_summary` to `a2a/messages.py`, in Spanish and English, and remove `Text.NOT_AVAILABLE` (agent-interface spec: Search update, Sources summary). Verify with `tests/unit/a2a/test_messages.py`: step number of total, source-kind labels, a result count or no results or failed, market labelled as offer prices, `other` counted, the note that validation and the answer are not yet available, and no query, domain, or URL in any text.
- [x] 4.2 In `a2a/executor.py`, send one search update per newly finished step, reset `research_step`, `evidence`, and `gaps` with the plan, complete with `sources_summary`, and end with the fixed failure when research kept no evidence (design 6). Verify with `tests/unit/a2a/test_executor.py`:
  - the update order: working, interpretation, plan, one update per step, completed
  - no search updates for an ambiguous request
  - every gap leading to failed after the search updates, with no provider text
  - a clarification follow-up not repeating an earlier round's search updates

## 5. Server wiring

- [x] 5.1 Let `server.create_app` accept an optional `search_tool`. By default it builds `BraveSearchTool` with a shared `httpx.AsyncClient`, closed in the Starlette lifespan (design 7). In `main()`, exit with status 1 and an error naming `BRAVE_SEARCH_API_KEY` when the key is empty. Verify with a unit test of the startup check (no secret values in the output). Extend `tests/integration/a2a/test_server.py` with a faked search tool to cover streaming with search updates, completion with the sources summary, and failure when every search is empty.
- [x] 5.2 Add `tests/integration/test_live_search.py`, marked `live` and skipped by default. It runs typical official (two-site INE/MIVAU), media (past month), and market queries against Brave, and checks that every result has an http(s) URL, a source type, and site-restricted results only from those sites. Update the `live` marker description in `pyproject.toml` to mention the search key. Verify that `pytest` skips it by default, and run it with `pytest -m live` when a key is available.

## 6. Architecture and project docs

- [x] 6.1 Update `docs/architecture/use-cases.drawio` ("Google Search" becomes "Brave Search") and `docs/architecture/physical-architecture.drawio` (the search node, the host, and the env-note variables). Verify by opening both diagrams and searching for `Google`, which should find nothing.
- [x] 6.2 Update `AGENTS.md` (the stack table's web-search row says Brave Search API, and the secrets line names Brave instead of Google) and the `README.md` status note that search is not available, and add the search step to its workflow description. Verify with `grep -n -i google AGENTS.md README.md`, which should find nothing about search.

## 7. Integration checks

- [x] 7.1 Run `pytest` for the agent, and `pnpm test:unit --run`, `pnpm lint`, and `pnpm build` in `web/`. All of them must pass. Report any check that is not configured instead of claiming it passed.
- [ ] 7.2 Run the agent with a real Brave key and LM Studio, ask a rents question in the web client, and confirm that it shows the search updates and the sources summary, with no queries, domains, or provider errors.

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
