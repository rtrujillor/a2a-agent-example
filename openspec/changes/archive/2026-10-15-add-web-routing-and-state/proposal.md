# Proposal

## Why

The web client is a single `App.vue` with one heading. Before building the
research chat, the app needs a routing and state foundation and a real home
page. That way the chat lands in a prepared place and doesn't force a
restructure later.

## What Changes

- Add client-side routing with history-mode URLs: `/` shows the home page, and
  any unknown path shows a not-found page with a link back home.
- Add an application state store, registered at startup and holding no
  domain state yet. The conversation store's shape is deliberately not decided
  in this change.
- Turn `App.vue` into a layout shell (header + routed view).
- Add a static home page in Spanish: title, a short description of what the
  agent researches, and what it does not do. The research chat will later live
  on this page.
- Set the document language to Spanish and give the page a proper title.
- Update AGENTS.md (stack table), `web/README.md`, and the Research Client
  node in `docs/architecture/physical-architecture.drawio`.

Out of scope: the chat UI, the A2A client, conversation state (context ID,
turns, streaming, cancellation), an About page, and any persistence.

## Capabilities

### New Capabilities
- `web-app-shell`: The web client's page structure: the home page, URL
  navigation between pages, and the not-found page.

### Modified Capabilities

None.

## Impact

- **Code:** `web/` only: `src/main.ts`, `src/App.vue`, new `src/router/`,
  `src/views/`, `src/test-utils/`, `index.html`, `src/__tests__/`.
- **Dependencies (web, pinned exactly):** `vue-router`, `pinia`.
- **Docs:** AGENTS.md, `web/README.md`,
  `docs/architecture/physical-architecture.drawio`.
- **Agent server:** none.
