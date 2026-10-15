# Tasks

## 1. Tailwind and shadcn-vue setup

- [x] 1.1 Add `tailwindcss` and `@tailwindcss/vite` (exact versions, newest at least two weeks old) and register the plugin in `vite.config.ts`; verify `pnpm build` succeeds
- [x] 1.2 Create `src/styles/main.css` with `@import "tailwindcss"`, import it once from `src/main.ts`, and remove any other global style entry; verify a utility class renders in `pnpm dev`
- [x] 1.3 Run the shadcn-vue CLI `init` with base color `neutral` and CSS path `src/styles/main.css`; verify `components.json`, `src/lib/utils.ts`, and the token block exist
- [x] 1.4 Pin every dependency the CLI added to exact versions, then run `pnpm format`; verify `package.json` has no `^`/`~` ranges for the new packages and `pnpm lint`, `pnpm build` pass

## 2. Tokens and themes

- [x] 2.1 Replace the CLI's `.dark` selector and `dark` variant with `@media (prefers-color-scheme: dark)` and `@custom-variant dark (...)` as in design.md; verify in the browser that switching the OS theme updates the app live, with no reload and no flash on load

- [x] 2.3 Set the system font stack and a minimal `.prose` base style (headings, lists, links, code) in `@layer base`; verify rendered sample Markdown HTML uses only token colors
- [x] 2.4 Check contrast for every foreground/background token pair in both themes (4.5:1 text, 3:1 focus ring and borders), adjust failing values, and record the measured ratios in the task notes; verify all pairs pass
  - Notes (light / dark, WCAG 2.x, computed from the oklch tokens with alpha composited): foreground on background 19.79 / 18.96; card and popover 19.79 / 17.16; primary 17.16 / 14.22; secondary and accent 16.42 / 14.48; muted-foreground on muted 5.05 / 5.83, on background 5.51 / 7.63, on card 5.51 / 6.91; destructive on background 4.76 / 6.84, on card 4.76 / 6.19; ring on background 4.73 / 4.18, on card 4.73 / 3.79; input border on background 3.36 / 3.77, on card 3.36 / 3.82.
  - Adjusted: light `--muted-foreground` 0.556 → 0.52, `--ring` 0.708 → 0.556, `--input` 0.922 → 0.64; dark `--input` 15% → 40% white. `--border` stays decorative (separators); `--input` is the component boundary. The 50% focus halo cannot reach 3:1, so the full-opacity `ring` color is the required indicator and the base outline now uses `outline-ring` (was `/50`).


## 4. Lint guard

- [x] 4.1 Implement `scripts/check-style-tokens.mjs` per design.md (hex colors, color functions, arbitrary values with raw literals; allow `var(...)` and attribute variants; skip `src/styles/`) and add it as `lint:tokens`; verify `pnpm lint` runs it and passes on the current code
- [x] 4.2 Add a Vitest test for the checker with fixtures: `#1d4ed8`, `bg-[#fff]`, and `p-[13px]` fail with file:line; `bg-primary`, `h-[var(--x)]`, and `data-[state=open]:` pass

## 5. Documentation and architecture

- [x] 5.1 Update AGENTS.md: add shadcn-vue + Tailwind 4 to the stack table; add web client rules (tokens only in `src/styles/main.css`, new looks become variants in `components/ui/`, no raw values, `pnpm lint` enforces it); verify the rules match the lint script
- [x] 5.2 Update `web/README.md` with the styles and `components/ui/` layout, how to add a primitive with the CLI, and the shadcn-vue version used; verify the documented command works
- [x] 5.3 Update the Research Client node in `docs/architecture/physical-architecture.drawio` to read "Vue.js SPA + shadcn-vue/Tailwind + A2A JS client"; verify the file still parses and opens in draw.io

## 6. Integration check

- verify `pnpm test:unit --run`, `pnpm lint`, and `pnpm build` all pass on the final state

## Workflow follow-up

- Archive the change once review is done, so `web-design-system` becomes a main spec.
