# Housing Access Web Client

Vue.js 3 + TypeScript SPA that sends research requests to the agent over A2A
and shows progress, answers, citations, and limitations. See the root
[README](../README.md) and [AGENTS.md](../AGENTS.md).

```text
src/
├── components/
│   └── ui/           # shadcn-vue primitives (vendored, owned by us)
├── composables/      # useResearchTask: task state and streaming
├── lib/utils.ts      # cn(): merges Tailwind classes
├── services/         # a2aClient: agent card, send, stream
├── types/            # Research request and answer types
├── styles/main.css   # the only place for tokens, themes, and base styles
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

## Design system

The client uses [shadcn-vue](https://shadcn-vue.com) 2.8.2 (Reka UI
primitives) with Tailwind CSS 4. `components.json` holds the CLI settings.

- **Tokens:** colors, radii, and fonts are CSS variables in
  `src/styles/main.css`, mapped to Tailwind utilities with `@theme inline`.
  Components use the utilities (`bg-primary`, `text-muted-foreground`), never
  raw values. Change a token there and every component follows.
- **Themes:** light and dark follow the operating system preference through
  `@media (prefers-color-scheme: dark)`; the `dark:` variant uses the same
  query. There is no manual toggle.
- **Fonts:** the system font stack; no web fonts are loaded.
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
