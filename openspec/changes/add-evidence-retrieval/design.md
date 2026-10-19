# Design

## Context

See proposal.md for why. Current state:

- `graph.py` runs `classify -> plan -> END`. The executor streams graph
  state (`stream_mode="values"`) and sends each update once, the first time
  the state holds it.
- `tools/base.py` already defines `SearchQuery`, `SourceResult`, and the
  `SearchTool` protocol. `tools/catalog.py` sets the source type from the
  domain. `tools/google_search.py` and `workflow/researcher.py` are empty
  stubs.
- `ResearchState.searches_used` exists but nothing sets it.
- `httpx==0.28.1` is already a pinned dependency, so the adapter needs no
  new package.
- Tests build `Settings(_env_file=None, model_name=...)` in many places, so
  any new required setting would touch every one of them.

## Goals / Non-Goals

**Goals:**
- One researcher node, with no model access, that the executor can report
  on step by step from streamed state alone.
- A Brave adapter behind the existing `SearchTool` protocol, so a later
  provider change only swaps the adapter.
- Every retrieval rule (limits, site filter, deduplication, gaps) testable
  with a fake tool and no network.

**Non-Goals:**
- Direct official-source adapters (INE Tempus API, BOE open data). They
  stay a later change, and `tools/official_sources.py` stays a stub.
- Fetching result pages, or Brave's summarizer and LLM-context endpoints.
- Replanning. The validator and its edge back to the planner come later;
  this change keeps `searches_used` correct for them.
- Running searches in parallel.
- Returning sources as a task artifact. That arrives with the synthesizer,
  together with citations.

## Decisions

### 1. Flow: a research node that runs one step per pass

```
START -> classify --(in_scope)--> plan -> research --(steps left)--> research
                \--(otherwise)--> END              \--(done)-------> END
```

`research` runs the step at `state["research_step"]`, stores its outcome,
and increments the cursor. A conditional edge loops back while
`research_step < len(plan.steps)`. Because each pass ends a node, the
executor's existing `values` stream shows each step's outcome as it
happens, with no new stream mode.

*Alternative:* one node that runs every step and emits progress through
LangGraph's `custom` stream (`get_stream_writer`). Rejected: it adds a
second stream mode to the executor, and an interrupted run would lose every
step instead of the current one. The loop is bounded by the plan length,
which is at most `max_searches_per_request`, far under LangGraph's recursion
limit of 25.

### 2. State and domain models

`SourceResult` and `SearchQuery` move to `domain/models.py`, because they
are evidence and request models and the state must hold them.
`tools/base.py` re-exports them, so current imports keep working. It also
defines `SearchErrorCategory` and `SearchToolError`, so the researcher
depends on the tool contract and not on the Brave adapter. New
domain models:

```
Evidence    step: int, source: SourceResult
SearchGap   step: int, reason: GapReason (empty | failed)
```

New `ResearchState` fields: `research_step: int`, `evidence:
list[Evidence]`, and `gaps: list[SearchGap]`. These are plain fields, not
reducers: the node writes the whole list each time. The executor's
`research_reset` clears all three along with the plan, for the same reason
it clears the plan today (decision 6).

### 3. Researcher node

`make_researcher(tools: Mapping[ToolName, SearchTool], settings, catalog,
clock)` returns the node. For one step it:

1. Builds a `SearchQuery` (query, `query_language`, freshness, sites,
   `max_results_per_search`).
2. Calls the tool. A `SearchToolError`, or any other exception from the
   tool, becomes a `failed` gap. A step that has no tool, or would exceed
   `max_searches_per_request`, also becomes a `failed` gap without a
   search.
3. Drops results whose URL is not `http`/`https`. For a step with sites, it
   also drops results whose host does not match one of `step.sites`, using
   `domain_matches`. It keeps at most `max_results_per_search` results.
4. Normalizes each URL for deduplication (lower-case host, no fragment, no
   trailing slash) and drops the ones already in `evidence`.
5. Appends the `Evidence` items, or an `empty` gap when none are left, and
   increments `searches_used` and `research_step`.
6. Never raises because evidence is missing. If the node raised on the last
   step, LangGraph would discard that step's update, so the last search
   update would never stream. The spec requires the failure to come after
   every search update. Instead, the executor fails the task when research
   ends with no evidence (decision 6).

The planner returns `research_step: 0` with every new plan, so a later
replan is researched from its first step.

The site filter checks against `step.sites` rather than the topic
allowlist: it is stricter, and the planner has already limited `sites` to
the allowlist.

### 4. Brave adapter (`tools/brave_search.py`)

`tools/google_search.py` is deleted. `BraveSearchTool(client:
httpx.AsyncClient, api_key, settings, catalog, clock, sleep)` implements
`SearchTool` with `name = ToolName.WEB_SEARCH`.

Request: `GET https://api.search.brave.com/res/v1/web/search`, with header
`X-Subscription-Token`.

| SearchQuery | Brave parameter |
|---|---|
| query + sites | `q = "<query> (site:a OR site:b)"`; a single site has no parentheses |
| max_results | `count` (capped at 20) |
| language | `search_lang`, from a small supported table, else `es` |
| always | `country=ES` |
| past_week / past_month / past_year | `freshness=pw` / `pm` / `py` |

Response (`web.results[]`):

| Brave | SourceResult |
|---|---|
| `url` | `url` |
| `title` | `title`, markup removed and entities decoded |
| `description` | `snippet`, same cleaning |
| `profile.name`, else `meta_url.hostname`, else the URL host | `publisher` |
| `page_age` (ISO datetime) | `published_at` (date part), else None |
| clock | `retrieved_at` |
| `catalog.source_type_for(url)` | `source_type` |

Markup is removed with the standard library (`html.parser` and
`html.unescape`), with no new dependency. A response without `web.results`
counts as an empty list, not an error.

The host is a constant in the adapter, not a setting: AGENTS.md allows only
configured hosts, and making it configurable would let `.env` point
searches anywhere.

### 5. Retries, backoff, and pacing

These live inside the adapter, so the researcher sees only results or a
`SearchToolError` with a category (`timeout`, `connection`, `rate_limited`,
`server`, `rejected`, `invalid_response`).

- Retried, up to `http_max_retries` times: `httpx.TimeoutException`,
  `httpx.TransportError`, HTTP 429, and HTTP 5xx. Backoff is `0.5 * 2**n`
  seconds. On a 429, the wait is the larger of the backoff and the
  provider's `Retry-After` header, capped at 10 s.
- Not retried: other 4xx responses (401/403 bad key, 422 bad parameter).
  An invalid JSON body is an `invalid_response` error, also not retried.
- Pacing: the adapter remembers when its last request started and sleeps
  until `search_min_interval_seconds` has passed (new setting, default
  `1.0`, `ge=0`). Steps run one after another, so a simple timestamp is
  enough. The overall `request_timeout_seconds` in the executor still
  bounds everything.

`sleep` and the clocks (`now` for `retrieved_at`, `monotonic` for pacing)
are injected, so the tests for timing and retries run instantly.

httpx logs each request URL, which includes the query, at INFO.
`observability.configure_logging` therefore sets the `httpx` logger to
WARNING. The adapter logs its own request parameters at DEBUG, and never
logs headers.

### 6. Executor progress

`report_progress` already sends the interpretation and the plan once. It
gains a `reported_steps` counter. When `state["research_step"]` exceeds
the counter, it sends one `search_update` per newly finished step, built in
`a2a/messages.py` from the plan step, the `Evidence` items for that step,
and any gap. At completion it sends `sources_summary(evidence, gaps,
language)` in place of `Text.NOT_AVAILABLE`, which is removed. Counts come
from `source.source_type`. Market sources use the existing "asking prices"
label, and `other` gets its own label.

When an in-scope task ends with no evidence, the executor logs `no search
kept a source` with the task identifier and fails with `Text.FAILURE`. The
researcher logs each gap's category, step by step.

### 7. Wiring and startup check

`server.create_app(settings, model, search_tool: SearchTool | None =
None)`: when no tool is given, it builds `BraveSearchTool` with a shared
`httpx.AsyncClient(timeout=settings.http_timeout_seconds)`. The client is
closed through the Starlette lifespan. Integration tests pass a fake tool.

`config.py`: `brave_search_api_key: SecretStr = SecretStr("")` and
`search_min_interval_seconds`. The two Google fields are removed. The key
stays optional in `Settings`, so existing tests are unchanged, and `main()`
checks it: if it is empty, it logs `BRAVE_SEARCH_API_KEY is required` and
exits with status 1 before starting Uvicorn.

*Alternative:* make the key a required setting. Rejected: it would change
every `Settings(...)` call in the tests, for a check that only matters when
the real server starts.

## Risks / Trade-offs

- **Brave may not honour `(site:a OR site:b)`.** → Mitigation: the
  researcher's own site filter means wrong-site results never get through.
  The worst case is fewer results. The live test checks a two-site query.
  If Brave does not honour it, the adapter falls back to one request per
  site. That stays within the spec, because a step still counts as one
  search; it only uses more of the provider's quota and the pacing
  interval.
- **`page_age` is Brave's estimate, not always the publication date.** →
  Mitigation: it is stored as the publication date only when present. The
  validator, later, treats dates as needing a check. Nothing claims it is
  the date of the reported event.
- **Retries one after another can exhaust the request time.** With the
  defaults (15 s timeout, 2 retries, up to 6 steps), the worst case passes
  120 s, and the task then fails and loses the evidence it already had. →
  Mitigation: accepted for now, since that worst case needs every step to
  hang. A per-research time budget can come with the validator.
- **Snippets are thin evidence.** → Accepted, and stated in the completion
  message. Fetching pages is a separate, security-reviewed change.
- **Brave's index covers Spanish official sites less well than Google's.**
  → Mitigation: the live test measures results for typical official steps
  (INE, BOE, MIVAU). Direct official adapters are the long-term answer.

## Migration Plan

1. Operators create a Brave Search API key and set `BRAVE_SEARCH_API_KEY`.
   They remove `GOOGLE_SEARCH_*` from `.env` (extra variables are ignored,
   so leaving them does no harm).
2. `.env.example`, `README.md`, and `AGENTS.md` (stack table and secrets
   line) are updated in the same change, and so are
   `docs/architecture/use-cases.drawio` ("Google Search" becomes "Brave
   Search") and `physical-architecture.drawio`.
3. Rollback: revert the change. The previous build needs no search key.

## Open Questions

- Which `search_lang` codes Brave accepts besides `es` and `en` (`ca`,
  `eu`, `gl`). Check against Brave's documentation during apply. Any
  unsupported code falls back to `es`, as the spec requires.
- Whether to also ask for Brave's `extra_snippets`, to get longer snippets
  for the validator. This can be added without changing the spec.
