# Design

## Context

`web/src` today: `main.ts` mounts `App.vue` with no plugins. `App.vue`
renders a single `<h1>`. `App.spec.ts` mounts it bare. The placeholders
`composables/useResearchTask.ts`, `services/a2aClient.ts` and
`types/research.ts` are empty (`export {}`), and `components/ui/` holds no
primitives yet. The design system (tokens, `lint:tokens`) is in place, and
every new view must use token utilities only. AGENTS.md requires exact version
pins and a stack-table and diagram update for new frameworks. Requirements
are in `specs/web-app-shell/spec.md`.

## Goals / Non-Goals

**Goals:**
- Router and store are wired once in `main.ts`, so later changes only add
  routes and stores.
- Tests can mount any view with the same plugins as the app, with fresh state
  per test.

**Non-Goals:**
- Any store with domain state. The conversation store's shape (context ID,
  turns, streaming, cancel) is decided in the chat change.
- Route guards, transitions, scroll behavior, lazy-route prefetching, i18n.
- Changing the empty placeholders in `composables/`, `services/`, `types/`.

## Decisions

### Layout

```
web/src/
+-- main.ts                 createApp(App).use(createPinia()).use(router).mount
+-- App.vue                 layout shell: <header> (RouterLink home) + <main><RouterView/></main>
+-- router/index.ts         routes table + createRouter(createWebHistory(BASE_URL))
+-- views/
|   +-- HomeView.vue        static Spanish content; future home of the chat
|   +-- NotFoundView.vue    "Página no encontrada" + RouterLink to "/"
+-- stores/                 created by the first real store (chat change)
+-- test-utils/mount.ts     mountWithPlugins(component, { route? })
```

### Router: vue-router, hand-written routes, history mode

| Path                | Name       | View                          |
| ------------------- | ---------- | ----------------------------- |
| `/`                 | `home`     | `HomeView` (eager)            |
| `/:pathMatch(.*)*`  | `notFound` | `NotFoundView` (lazy import)  |

- **Hand-written routes table.** Alternative: file-based routing. Rejected:
  with two routes, hidden conventions and a codegen step cost more than they
  save.
- **`createWebHistory`.** Real paths, which the spec requires (no hash). Vite's
  dev and preview servers already fall back to `index.html` for unknown
  paths. Alternative: `createWebHashHistory`. Rejected by the spec.
- **Home is eager, other views are lazy.** Home is the landing page and must
  not wait for a second chunk. Every later view uses `() => import(...)`.
- **Navigate by route name** (`{ name: 'home' }`), never by hard-coded
  path strings in components.
- **A factory, not a module singleton.** `router/index.ts` exports `routes`
  and a `createAppRouter(history)` function, plus the app's default instance.
  Tests build their own router with `createMemoryHistory()`, so no state leaks
  between tests.

### State: Pinia, registered, no stores yet

- **Pinia with setup-style stores** (`defineStore('id', () => {...})`).
  Setup stores read like the Composition API used everywhere else.
  Alternative: module-level singleton composables. Rejected: hidden global
  state, no devtools timeline, and manual reset between tests.
- **No placeholder store.** A store with nothing meaningful in it would be
  deleted or reshaped by the chat change. This change only registers Pinia and
  fixes the conventions below in `web/README.md`:
  - One store per file in `src/stores/`, exported as `use<Name>Store`.
  - Stores call `services/`; components never call `services/` directly.
  - State is in memory only. No persistence plugin and no `localStorage`
    until persistence is designed (AGENTS.md).
- **Test isolation:** `mountWithPlugins` installs a fresh `createPinia()` per
  mount. Store unit tests use `setActivePinia(createPinia())` in `beforeEach`.
  Alternative: `@pinia/testing`. Deferred until a store needs action
  stubbing; adding it now would be an unused dependency.

### Layout shell and pages

- `App.vue` owns the header and the `<main>` landmark. Views render only their
  content, so the chat can later take full height inside `<main>`.
- The header's app name is a `RouterLink` to `{ name: 'home' }`.
- Home content is static text in the template, in Spanish: the title "Acceso a
  la vivienda en España", what the agent researches (prices, rents, wages,
  supply, public housing, tenant rights, tourism and short-term rentals,
  legislation, news and social movements), and what it does not provide.
  Copy is kept neutral and descriptive, consistent with AGENTS.md scope.
- Styling uses token utilities only (`bg-background`, `text-muted-foreground`,
  ...). No shadcn primitive is needed yet. Adding one just for a link would
  be premature.
- `index.html`: `lang="es"`, `<title>Acceso a la vivienda en España</title>`.

### Versions

`vue-router` and `pinia`: newest stable release that is at least two weeks
old at apply time, pinned exactly (no `^`/`~`), installed with pnpm. Record the
chosen versions in `web/README.md`.

## Risks / Trade-offs

- [History mode needs a server fallback outside Vite] → Local dev and preview
  already handle it. Any future static hosting must rewrite unknown paths to
  `index.html`. Noted in `web/README.md`.
- [Major-version drift: vue-router's latest major may differ from the API
  sketched here] → The decisions above use only APIs stable across recent
  majors (`createRouter`, `createWebHistory`, `createMemoryHistory`,
  `RouterLink`, `RouterView`). Verify at install time and note any difference
  in the task.
- [No store yet, so the Pinia wiring is untested by real use] → One test
  asserts the active Pinia instance exists when the app is mounted via
  `mountWithPlugins`.
