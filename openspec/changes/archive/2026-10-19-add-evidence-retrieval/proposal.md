# Proposal

## Why

The agent builds a research plan but runs none of it: an in-scope task ends
with "source search is not available yet". The use cases *Retrieve official
evidence* and *Search current web information* come right after planning and
are the next step toward cited answers. The planned provider, Google's Custom
Search JSON API, is closed to new customers and reported to shut down on
2027-01-01, and new engines can no longer search the whole web, so it can't
serve media steps. Brave Search API replaces it.

## What Changes

- **BREAKING (configuration):** replace Google Programmable Search with the
  Brave Search API. `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID` are
  removed and `BRAVE_SEARCH_API_KEY` is added. The only outbound search host
  is `api.search.brave.com` over HTTPS.
- Add a Brave adapter for the existing `web_search` tool. It maps a
  `SearchQuery` (query, sites, language, freshness, result count) to a Brave
  request with country Spain, and maps each result to a `SourceResult`. The
  agent sets the source type from the domain, as today.
- Add a researcher node and the edge `plan -> research`. It runs each plan
  step as one search within the per-request budget, the per-search result
  limit, and the request timeout. It counts the searches used, drops
  duplicate URLs, and keeps each result linked to its step.
- Official steps keep only results whose domain is on the topic's
  allowlist, because Brave has no engine-level site list.
- Partial evidence: a step that fails or returns nothing is recorded as a
  gap and the other steps continue. The task fails only when no step
  returns any result.
- Snippets only: the agent does not fetch result pages in this change.
  Snippets are untrusted data, with markup stripped.
- Progress: one working update per search step, in the request's language,
  with the step's sub-question and source kind and the number of results.
  Queries and domains are never shown.
- The completed task reports how many sources were found, by source type,
  in place of "source search is not available yet". Validation and the
  synthesized answer remain future changes.
- Update `AGENTS.md`, `README.md`, `.env.example`, and the use-case and
  physical-architecture diagrams for the new provider.

## Capabilities

### New Capabilities
- `evidence-retrieval`: running a research plan's steps against search
  tools. It covers the search provider, budget and limit enforcement,
  timeouts and retries, rate limits, allowlist filtering of official
  results, deduplication, gaps when steps fail, and handling of untrusted
  snippets.

### Modified Capabilities
- `agent-interface`: streamed progress gains one update per search step
  after the plan update. An in-scope task completes with a summary of the
  sources found, and fails with the fixed message when no search returns
  results.

## Impact

- Code: `tools/google_search.py` is replaced by `tools/brave_search.py`; new
  `workflow/researcher.py` logic; `graph.py`, `state.py` (evidence and
  gaps), `config.py`, `a2a/executor.py`, `a2a/messages.py`.
- Configuration: new `BRAVE_SEARCH_API_KEY`; the Google variables are
  removed. Operators must create a Brave API key.
- Dependencies: an async HTTP client, if the stack does not already include
  one (to be confirmed in design).
- Tests: unit tests for the adapter (with a faked HTTP layer), the
  researcher, and the executor mapping; in-process integration tests with a
  faked search tool; one live Brave test, skipped by default.
- Docs: `AGENTS.md` stack table and secrets line, `README.md`,
  `.env.example`, `docs/architecture/use-cases.drawio`,
  `docs/architecture/physical-architecture.drawio`.
- Web client: no change expected; it already shows each agent status
  update as a step.
