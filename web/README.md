# Housing Access Web Client

Vue.js 3 + TypeScript SPA that sends research requests to the agent over A2A
and shows progress, answers, citations, and limitations. See the root
[README](../README.md) and [AGENTS.md](../AGENTS.md).

```text
src/
├── components/
│   ├── ResearchRequestForm.vue  # question form on the home page
│   └── ui/           # shadcn-vue primitives (vendored, owned by us)
├── lib/utils.ts      # cn(): merges Tailwind classes
├── router/index.ts   # routes table, createAppRouter(history), app router
├── services/         # a2aClient: agent card, send, stream
├── stores/           # Pinia stores: research.ts (useResearchStore)
├── test-utils/       # mountWithPlugins(): fresh Pinia + memory router
├── types/            # Research request and answer types
├── views/            # Routed pages: HomeView, NotFoundView
├── styles/main.css   # the only place for tokens, themes, and base styles
├── App.vue           # layout shell: header + <main><RouterView/></main>
└── __tests__/        # Vitest unit tests
scripts/
└── check-style-tokens.mjs  # lint:tokens, rejects raw style values
```

## Commands

```bash
cp .env.example .env   # set VITE_AGENT_URL
pnpm install
pnpm dev               # http://localhost:5173
pnpm test:unit
pnpm lint
pnpm build             # type-check + production build
```

## Routing and state

[Vue Router](https://router.vuejs.org) 5.3.1 and [Pinia](https://pinia.vuejs.org)
4.0.3, pinned exactly. Both are registered once in `src/main.ts`.

| Path               | Name       | View                         |
| ------------------ | ---------- | ---------------------------- |
| `/`                | `home`     | `HomeView` (eager)           |
| `/:pathMatch(.*)*` | `notFound` | `NotFoundView` (lazy import) |

### Adding a route

1. Create the page in `src/views/<Name>View.vue` using token utilities only.
2. Add an entry to `routes` in `src/router/index.ts` **before** `notFound`,
   with a `name` and a lazy component: `component: () => import('@/views/<Name>View.vue')`.
   Only `HomeView` is imported eagerly.
3. Link to it by name, never by a hard-coded path:
   `<RouterLink :to="{ name: '<name>' }">`.
4. Test it with `mountWithPlugins(App, { route: '/<path>' })` from
   `src/test-utils/mount.ts`, which builds a fresh Pinia and a memory-history
   router per call.

### History mode

URLs are real paths (`createWebHistory`), not hashes. `pnpm dev` and
`pnpm preview` already serve `index.html` for unknown paths. Any other static
host must rewrite unknown paths to `index.html`, or direct loads and reloads
of pages other than `/` return a server 404.

### Pinia conventions

- Setup stores only: `defineStore('<id>', () => { ... })`.
- One store per file in `src/stores/`, exported as `use<Name>Store`.
- Stores call `services/`; components use stores and never call `services/`
  directly.
- State lives in memory only. No persistence plugin. The one exception is
  the theme choice (`useThemeStore`, `src/stores/theme.ts`), which is kept in
  `localStorage` under the key `theme`. Research state is never stored.
- Store unit tests call `setActivePinia(createPinia())` in `beforeEach`.

## Research request

The home page's `ResearchRequestForm` sends one question to the agent. Data
flows one way: component → `useResearchStore` (`src/stores/research.ts`) →
`a2aService` (`src/services/a2aClient.ts`) → agent.

- **Agent URL:** `VITE_AGENT_URL` in `.env` (see `.env.example`). It is a
  public address, never a secret. The service reads the agent card at
  `<VITE_AGENT_URL>/.well-known/agent-card.json` and uses the endpoint the card
  declares. The agent must allow this client's origin in CORS.
- **SDK boundary:** `services/a2aClient.ts` is the only module that imports
  `@a2a-js/sdk`. Everything else uses the types in `src/types/research.ts`.
- **Store states:**

  | Status        | Meaning                                                       |
  | ------------- | ------------------------------------------------------------- |
  | `idle`        | Nothing sent yet                                              |
  | `invalid`     | Empty question or over `MAX_QUESTION_LENGTH` (2000); not sent |
  | `submitting`  | Waiting for the agent's first stream event                    |
  | `submitted`   | Accepted; `taskId` and `contextId` are kept, stream open      |
  | `unreachable` | Agent card, network, CORS, or empty-stream failure            |

  Only one request runs at a time. A new submission closes the previous stream
  and starts a new context.

## Design system

The client uses [shadcn-vue](https://shadcn-vue.com) 2.8.2 (Reka UI
primitives) with Tailwind CSS 4. `components.json` holds the CLI settings.

- **Tokens:** colors, radii, and fonts are CSS variables in
  `src/styles/main.css`, mapped to Tailwind utilities with `@theme inline`.
  Components use the utilities (`bg-primary`, `text-muted-foreground`), never
  raw values. Change a token there and every component follows.
- **Palette:** civic/editorial. Warm "paper" neutrals and a deep blue
  primary in light, blue "ink" in dark. Domain tokens: `source-official`,
  `source-media`, `source-market`, `source-other` (citation badges) and
  `notice` (limitation notices, distinct from `destructive` errors). The
  contrast ratios of every pair are recorded in `main.css`; recheck them when
  changing a value.
- **Themes:** the header's theme control offers Claro, Oscuro, and Sistema
  (the default). Dark tokens live under `.dark`, and the `dark:` variant
  matches that class. An inline script in `index.html` applies the saved
  choice before first paint; `useThemeStore` keeps it in sync and follows
  the system live on Sistema. Keep the script and the store on the same
  storage key and values.
- **Fonts:** system fonts only, and no web fonts are loaded. Headings use a
  serif stack (`font-heading`: Charter, Iowan Old Style, Georgia, ...);
  interface and body text use the system sans-serif stack.
- **Motion:** decorative animation is always prefixed `motion-safe:`.
- **Answer prose:** wrap rendered Markdown in `.prose` for token-based
  headings, lists, links, and code.
- **Lint guard:** `pnpm lint` runs `lint:tokens`, which fails on hex colors,
  color functions, and arbitrary Tailwind values with literals (`p-[13px]`)
  outside `src/styles/`. Mark a rare exception with a `style-tokens-allow`
  comment on that line.

### Adding a primitive

```bash
pnpm dlx shadcn-vue@2.8.2 add button   # writes src/components/ui/button/
```

Then:

1. Pin any dependency the CLI added (for example `reka-ui`) to an exact
   version in `package.json` and run `pnpm install`.
2. Run `pnpm format` and `pnpm lint`. Generated components can contain raw
   values (the button uses `rounded-[min(var(--radius-md),8px)]`); replace
   them with token utilities such as `rounded-md`.
3. New looks become CVA variants in `src/components/ui/`, not one-off classes
   in app components.
4. Check `git diff src/styles/main.css`: the CLI may insert a Google Fonts
   `@import` or duplicate base styles. Revert those edits; tokens are
   maintained by hand.
5. When the CLI asks to overwrite an existing primitive, answer no unless the
   update is intended.
