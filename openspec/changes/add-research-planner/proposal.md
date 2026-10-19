# Proposal

## Why

An in-scope request currently ends right after classification, with a note
that research is not available yet. "Plan bounded research" is the next step
in `docs/architecture/use-cases.drawio`, and every later step (retrieve,
validate, synthesize) runs from a plan. The planner is also where the
research limits, the preference for official sources, and the privacy of
search queries are enforced. Fixing those rules and the plan-to-tool contract
now, before any search adapter exists, keeps the next retrieval change small
and keeps the bounds out of the model's hands.

## What Changes

- Add a planning step after classification for in-scope requests. The
  language model proposes a research plan as structured output. Each step has:
  - a sub-question, in the user's language
  - the tool that runs it
  - the search query and the query's language
  - the expected source kind: official, media, or market
  - an optional freshness filter
  - optional site restrictions
- Enforce the plan in code, not in the model:
  - Drop steps with an unknown tool, an empty query, or site restrictions
    outside the topic's official-domain allowlist.
  - Truncate to the search budget for this iteration.
  - Require at least one official-restricted step when the topic has
    official domains.
  - If no valid plan remains, retry within the configured bounds, then end
    the task as `failed`.
- Bound the search budget with the existing limits. The first plan may use at
  most `MAX_SEARCHES_PER_REQUEST - MAX_PLANNER_ITERATIONS` searches, which
  keeps at least one search for each allowed replan. The budget is a ceiling;
  a plan may use fewer searches.
- Add a tool catalog owned by the code. It has one tool, `web_search`, with
  optional site restrictions. Each topic has an allowlist of official domains
  (INE, MIVAU, BOE, Banco de España, and so on). Official evidence is
  retrieved as site-restricted web search for now. The catalog is an
  enumeration, so dedicated dataset tools can be added later without changing
  the plan shape.
- Define the retrieval contract in `tools/`: a search tool interface and a
  source result carrying URL, title, publisher, publication date, retrieval
  date, source type, and snippet. The code, not the model, sets the source
  type from the result's domain. No adapter is built in this change.
- Keep personal details out of queries. Queries hold only the researchable
  core (topic, place, period), never the user's own circumstances. The
  planning model sees only the classification, never the user's raw
  messages.
- Show the plan to the user as a progress step: the sub-questions in the
  user's language, each with its source kind. Market sources are labelled as
  offer prices. Raw queries and site filters are not shown. The task then
  completes with a note that source search is not available yet.

Out of scope:
- Search and official-source adapters, outbound HTTP, and the URL-fetching
  rules.
- Running the plan, validating evidence, replanning from validator gaps, and
  synthesis. The planner accepts the budget already spent and the iteration
  number, but nothing replans yet.
- Dedicated dataset tools, such as the INE or Banco de España APIs.
- Web client changes. The progress panel already shows agent status text.

## Capabilities

### New Capabilities
- `research-planning`: How the agent turns a classified request into a
  bounded research plan: the plan steps, the tool catalog and official-domain
  allowlists, budget enforcement, the official-source requirement, the
  privacy of queries, the plan shown to the user, the planning failure, and
  the retrieval contract that plan steps target.

### Modified Capabilities
- `agent-interface`: For an in-scope request, the stream now carries a plan
  update after the interpretation update, and the completed message says
  source search is not available yet. A planning failure ends as `failed`.

`request-classification` is unchanged: its interpretation report already
comes "before continuing".

## Impact

- **Code:** `src/housing_access_agent/`:
  - `domain/` gets plan, step, tool, and source-kind models and enums
  - `tools/base.py` gets the search tool interface and the source result
  - `tools/catalog.py`, new: the tool catalog and the official-domain
    allowlists by topic
  - `workflow/planner.py`
  - `prompts.py` gets the planner prompt
  - `state.py` gets the plan, searches used, and the iteration
  - `graph.py`: classify, then plan, then end
  - `a2a/messages.py` gets the plan summary and the new completion note
  - `a2a/executor.py` reports the plan step
  - `server.py` wires the planner

  `researcher.py`, `validator.py`, `synthesizer.py`, `google_search.py`, and
  `official_sources.py` stay placeholders.
- **Tests:** unit tests for the planner (budget, filtering, official
  requirement, retries, injected instructions, personal details), the catalog,
  the domain models, the source-type rules, and the plan summary. Updated
  executor, graph, and A2A integration tests for the new stream order. All use
  the fake chat model and need no network.
- **Configuration:** none. `MAX_PLANNER_ITERATIONS`,
  `MAX_SEARCHES_PER_REQUEST`, and `HTTP_MAX_RETRIES` are used as they are.
  `MAX_RESULTS_PER_SEARCH` stays unused until retrieval exists.
- **Dependencies:** none.
- **Docs:** `README.md` (status and how the limits are spent). The diagrams
  need no change: the C3 Research Planner, its "research plan" flow, and the
  Research State (which already lists the plan) exist.
