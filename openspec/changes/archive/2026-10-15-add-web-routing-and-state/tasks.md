# Tasks

## 1. Dependencies

- [x] 1.1 Add `vue-router` and `pinia` with pnpm at exact versions (newest stable, at least two weeks old); verify `package.json` has no `^`/`~` on them, `pnpm-lock.yaml` updated, and no npm/yarn lockfile appeared
- [x] 1.2 Check the installed vue-router major against the APIs in design.md (`createRouter`, `createWebHistory`, `createMemoryHistory`, `RouterLink`, `RouterView`); verify `pnpm type-check` passes on a scratch import, and note any API difference in this task
  - Note: installed vue-router 5.3.1 and pinia 4.0.3 (5.4.0 / 4.1.0 are under two weeks old). vue-router 5 keeps the core API from v4 (`createRouter`, `createWebHistory`, `createMemoryHistory`, `RouterLink`, `RouterView`) unchanged; it only adds optional file-based routing (`vue-router/vite`, `vue-router/auto-routes`), which this change does not use. No design difference.

## 2. Router, store and layout shell

- [x] 2.1 Create `src/router/index.ts` exporting `routes`, `createAppRouter(history)` and the default history-mode router, with `home` (eager `HomeView`) and `notFound` (`/:pathMatch(.*)*`, lazy `NotFoundView`); verify `pnpm type-check` passes
- [x] 2.2 Register Pinia and the router in `src/main.ts`; verify `pnpm dev` loads `/` without console errors
- [x] 2.3 Add `src/test-utils/mount.ts` with `mountWithPlugins(component, { route })` that installs a fresh Pinia and a memory-history router, then awaits `router.isReady()`; verify by the tests in 2.5
- [x] 2.4 Turn `src/App.vue` into the layout shell: header with the app name as a `RouterLink` to `{ name: 'home' }`, and `<main>` with `<RouterView />`, using token utilities only; verify `pnpm lint` (including `lint:tokens`) passes
- [x] 2.5 Rewrite `src/__tests__/App.spec.ts` with `mountWithPlugins`: the header shows the app name, the header link goes to `/`, and a Pinia instance is active; verify `pnpm test:unit --run` passes

## 3. Pages

- [x] 3.1 Create `src/views/HomeView.vue` with the static Spanish content from design.md (title, what the agent researches, what it does not provide), token utilities only; verify `pnpm lint` passes
- [x] 3.2 Create `src/views/NotFoundView.vue` ("Página no encontrada" + `RouterLink` to `{ name: 'home' }`); verify `pnpm lint` passes
- [x] 3.3 Add router/view tests: `/` renders the home title, description and limits; `/no-existe` renders the not-found page with the route path unchanged and a link to `/`; push then `router.back()` returns to `home`; verify `pnpm test:unit --run` passes
- [x] 3.4 Set `lang="es"` and `<title>Acceso a la vivienda en España</title>` in `index.html`; verify in `pnpm dev` that the tab title shows and that loading `http://localhost:5173/no-existe` directly shows the not-found page

## 4. Documentation and architecture

- [x] 4.1 Update `web/README.md`: `router/`, `views/`, `stores/`, `test-utils/` in the layout tree; how to add a route; Pinia conventions from design.md (setup stores, `use<Name>Store`, stores call services, in-memory only); the history-mode fallback note; pinned versions; verify the documented paths exist
- [x] 4.2 Update AGENTS.md: in the stack table, the web client row includes Vue Router (history mode) and Pinia (setup stores, in memory). In the Web client rules, components never call `services/` directly. Verify the text matches design.md
- [x] 4.3 Update the Research Client node and the mapping-table row in `docs/architecture/physical-architecture.drawio` to mention Vue Router + Pinia, and set its repo location to `web/`; verify the file is valid XML (`xmllint --noout`) and opens in draw.io
  - Note: `xmllint --noout` passes; only text inside two `value` attributes changed. The "opens in draw.io" check was not run because draw.io is not installed on the apply machine.

## 5. Integration check

- [x] 5.1 Run `pnpm test:unit --run`, `pnpm lint` and `pnpm build` in `web/`; verify all three pass, and that `pnpm preview` serves `/` and `/no-existe` correctly

## Workflow follow-up

- Archive the change once review is done, so `web-app-shell` becomes a main spec.
