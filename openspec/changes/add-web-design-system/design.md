# Design

## Context

`web/` is a fresh create-vue scaffold: Vue 3, TypeScript, Vite, Vitest,
ESLint/Oxlint, Prettier, pnpm. It has no styles yet. The `@` → `src` alias
already exists in `vite.config.ts` and `tsconfig.app.json`, which shadcn-vue
requires. AGENTS.md requires pinned dependencies, and diagram updates when the
stack changes. Requirements are in `specs/web-design-system/spec.md`.

## Goals / Non-Goals

**Goals:**
- One file (`src/styles/main.css`) holds every visual decision.
- Vendored primitives own accessibility; app components only compose them.
- Raw values are caught mechanically, not by review.

**Non-Goals:**
- Manual theme toggle, custom web fonts, animation design.

## Decisions

### Layout

```
web/
+-- components.json          shadcn-vue CLI config (style, base color, aliases, css path)
+-- scripts/check-style-tokens.mjs
+-- src/
    +-- main.ts              imports ./styles/main.css once
    +-- styles/main.css      tokens + Tailwind mapping + base layer
    +-- lib/utils.ts         cn() helper (shadcn's `cn` package: class merging for Tailwind)
    +-- components/ui/       to organizae the components
```

### Token layers

```
 Tailwind palette (oklch)          primitives, never referenced by components
          |
          v
 :root / dark  in main.css         semantic: --background --foreground --primary
                                   --muted --accent --destructive --border --ring --radius
                                   domain:   --source-{official,media,market,other}[-foreground]
                                             --warning --warning-foreground
          |
          v  @theme inline
 utilities: bg-primary, text-source-official, ring-ring ...   <- only thing components use
```

- **Use shadcn-vue's semantic names** and add domain tokens in the same
  pattern. Alternative: our own naming scheme. Rejected: it would fight every
  generated component.
- **Domain styles are variants, not classes.** Badge gains `official`,
  `media`, `market`, and `other` variants; Alert gains `warning` (limitation),
  separate from `destructive` (error). Variants are defined once with CVA in
  `components/ui/`. New looks become new variants, never one-off classes in app
  components.

### Theme switching: CSS only

Dark tokens live under `@media (prefers-color-scheme: dark)`, and Tailwind's
`dark` variant is redefined to that same media query
(`@custom-variant dark (@media (prefers-color-scheme: dark))`). Because no
JavaScript is involved, there is no flash of the wrong theme and switching is
live, which satisfies both theme scenarios.

Alternative: the shadcn default, a `.dark` class set by a script. Rejected for
now: it needs an inline script in `index.html` plus a `matchMedia` listener,
for a toggle that is out of scope. Migration path when a toggle is added:
change the `@custom-variant` selector and the dark-token selector to `.dark`,
and add the script.

### Lint guard

`scripts/check-style-tokens.mjs` runs as `lint:tokens`; the existing `lint`
script picks it up through `run-s "lint:*"`. It scans `src/**/*.{vue,ts}`,
excluding `src/styles/`, and fails with file:line on:

- hex colors: `#rgb`, `#rrggbb`, `#rrggbbaa`;
- color functions: `rgb(`, `rgba(`, `hsl(`, `hsla(`, `oklch(`, `oklab(`;
- arbitrary values that contain a raw literal, for example `p-[13px]`,
  `w-[2.5rem]`, or `bg-[#…]`.

It allows arbitrary values that only reference tokens or variables
(`h-[var(--reka-select-trigger-height)]`) and attribute variants
(`data-[state=open]:`). Vendored components use both legitimately; a blanket
`-[` ban would break them.

Alternative: an ESLint Tailwind plugin. Rejected: Tailwind 4 support is
uncertain, and a 40-line script is enough and easy to reason about.

### Other choices

- **Fonts:** the system font stack. No web-font requests (privacy, no
  external fetches).
- **Icons:** the Lucide package the shadcn-vue CLI selects.
- **Base color:** `neutral`, and `--primary` stays neutral (no hue). Every hue
  carries a Spanish party association, so color appears only in labeled
  source badges. Values can be retuned later by editing tokens only.
- **Focus indicator:** the full-opacity `ring` color (border or outline) is the
  indicator that must meet 3:1. The translucent `ring/50` halo that shadcn-vue
  components add is decorative.
- **Versions:** every new dependency is pinned exactly (no `^`), using the
  newest release that is at least two weeks old. The CLI installs with ranges,
  so pinning is an explicit step.
- **Contrast:** verified for each foreground/background token pair in both
  themes with a contrast checker, and the results recorded in the task.
  Automating this would need a color-parsing dependency; not worth it for
  about 12 pairs.

## Risks / Trade-offs

- [The shadcn-vue CLI output does not match the project's lint and Prettier
  rules] → run `pnpm format` and `pnpm lint` right after generation; commit
  generated files only once they are clean.
- [Vendored components drift from upstream] → accepted; we own them. Record
  the shadcn-vue version in `web/README.md` for reference.
- [CSS-only dark mode makes a future toggle a small refactor] → the migration
  path is documented above and touches only `main.css` plus one script.
- [Token-check false positives, e.g. `#` in a URL fragment inside a `.ts` file]
  → match hex only in style contexts (`class`, `style`, `<style>` blocks) and
  add an explicit allow comment for rare exceptions.
- [jsdom cannot evaluate media queries or contrast] → theme and contrast
  scenarios are verified manually in the browser; unit tests cover variants
  and labels.
