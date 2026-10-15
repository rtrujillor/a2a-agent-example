# Housing Access Web Client

Vue.js 3 + TypeScript SPA that sends research requests to the agent over A2A
and shows progress, answers, citations, and limitations. See the root
[README](../README.md) and [AGENTS.md](../AGENTS.md).

```text
src/
├── components/       # UI components
├── composables/      # useResearchTask: task state and streaming
├── services/         # a2aClient: agent card, send, stream
├── types/            # Research request and answer types
└── __tests__/        # Vitest unit tests
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
