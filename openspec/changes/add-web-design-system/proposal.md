# Proposal

## Why

The web client has no styling foundation yet. Before building the research UI
(request form, streamed progress, answer, citations), we need one design system
so styles are defined once, themes switch without touching components, and look consistent everywhere.

## What Changes

- Adopt **shadcn-vue** (Reka UI primitives + Tailwind CSS 4) as the web
  client's component foundation.
- Add a single style entry, `web/src/styles/main.css`, holding all semantic
  design tokens for light and dark themes, their mapping to Tailwind, and base
  typography including answer prose.
- Add domain tokens and badge variants for source types: official, media,
  market, other; plus a warning style for limitations.
- Follow the operating system's light/dark preference.
- Add a lint guard that rejects raw colors and arbitrary Tailwind values in
  Vue files.
- Update AGENTS.md (stack and web client rules), `web/README.md`, and the
  physical architecture diagram.

Out of scope: A2A communication, research UI components, Markdown rendering
and sanitization, a manual theme toggle.

## Capabilities

### New Capabilities
- `web-design-system`: Central design tokens, light and dark themes, shared UI
  primitives and variants, and the rule that components consume tokens instead
  of raw style values.

### Modified Capabilities

None.

## Impact

- **Code:** `web/` only: `vite.config.ts`, `src/main.ts`, new `src/styles/`,
  `src/lib/utils.ts`, `src/components/ui/`, `components.json`,
  `package.json` (lint script).
- **Dependencies (web, pinned):** `tailwindcss`, `@tailwindcss/vite`,
  `reka-ui`, `class-variance-authority`, `clsx`, `tailwind-merge`, a Lucide
  icon package, and the animation helper the shadcn-vue CLI selects.
- **Docs:** AGENTS.md, `web/README.md`,
  `docs/architecture/physical-architecture.drawio`.
- **Agent server:** none.
