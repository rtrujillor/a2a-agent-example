# Design

## Context

See proposal.md for motivation. Current state of `web/`:

- `src/styles/main.css` holds the stock shadcn-vue `neutral` tokens. Dark
  tokens sit under `@media (prefers-color-scheme: dark)`, and the `dark`
  variant is redefined to that media query. The archived
  `add-web-design-system` design planned `--source-*` and `--warning` tokens
  and named this change's migration path (switch to a `.dark` class plus a
  pre-paint script). Those tokens were never added.
- `src/components/ui/` has only `button` and `textarea`. `components.json`
  uses style `reka-vega`, lucide icons, and the `cn` package.
- The `Textarea` primitive already has `field-sizing-content`.
- `ResearchRequestForm.vue` owns validation messages, ⌘/Ctrl+Enter, and the
  `aria-live` status region. The research store stops at `submitted`.
- `web/README.md` says state is in memory only, with no `localStorage`.
- `pnpm lint:tokens` rejects raw colors and literal arbitrary values outside
  `src/styles/`.

Requirements: `specs/web-design-system`, `specs/web-app-shell`,
`specs/research-request` in this change.

## Goals / Non-Goals

**Goals:**
- The visual identity lives entirely in `main.css` tokens and `ui/` variants,
  so later screens get it for free.
- The theme switch is invisible in cost: no flash, no layout shift, and system
  behavior unchanged for users who never touch it.
- App components stay thin and compose primitives without one-off styling.

**Non-Goals:**
- Wiring the research view (progress steps, answer, citations). Only its
  primitives and variants are added here.
- Web fonts, illustration assets, icons beyond lucide.
- Any change to the agent, the A2A client, or the architecture diagrams.

## Decisions

### 1. Token palette: civic/editorial in oklch

Semantic shadcn-vue names are kept; only values change. Starting values, tuned
during implementation until every pair passes AA:

```
                 light ("paper")          dark ("ink")
  background     0.99  0.004  85          0.17  0.015 255
  foreground     0.20  0.02  255          0.96  0.005  85
  card           1     0      0           0.21  0.018 255
  primary        0.42  0.12  255          0.75  0.10  250
  primary-fg     0.98  0.005  85          0.17  0.015 255
  muted          0.96  0.006  85          0.25  0.015 255
  muted-fg       0.48  0.015  60          0.72  0.015 250
  border         0.90  0.008  85          1 0 0 / 10%
  ring           0.42  0.12  255          0.75  0.10  250
```

- Neutrals have a slight warm tint (hue around 85) in light mode and a
  blue-ink tint (hue around 255) in dark mode. Pure gray reads as the
  framework default; tinted neutrals give the palette character without
  adding hues.
- `--radius` goes from `0.625rem` to `0.5rem` for a crisper, printed feel.
  Depth comes from hairline borders, not shadows.
- Unused shadcn tokens (`sidebar-*`) are removed to keep the file readable.
  `chart-*` stays for future data visualization.

Alternative: keep `neutral` and add a single accent. Rejected because it was
the main reason the UI reads as generic.

### 2. Domain tokens and variants

```
  --source-official  [-foreground]   primary blue family
  --source-media     [-foreground]   teal
  --source-market    [-foreground]   amber
  --source-other     [-foreground]   neutral (muted)
  --notice           [-foreground]   amber-tinted surface + dark amber text
  --destructive                       unchanged role (errors)
```

These are mapped with `@theme inline` like the rest. `Badge` gains
`official | media | market | other` CVA variants and `Alert` gains `notice`
next to `destructive`. The limitation token is named `notice`, not the
`warning` the earlier design suggested: a limitation is information about
the evidence, not a warning about the user's action.

### 3. Typography: system serif headings

```css
--font-heading: 'Charter', 'Bitstream Charter', 'Iowan Old Style', 'Sitka Text',
                Cambria, Georgia, ui-serif, serif;
```

This is defined in `@theme`, replacing the `--font-heading: var(--font-sans)`
alias. Body and interface text keep the system sans-serif stack. Headings use
`text-balance` and paragraphs use `text-pretty`. The `.prose` headings already
use `font-heading`, so answer Markdown picks up the change automatically.

Alternative: self-hosted Source Serif 4 and Inter via `@fontsource`. Rejected
for now (two dependencies, about 100 KB). Switching later only changes this
token.

### 4. Theme: class-based dark variant, store over `useColorMode`

```
 index.html <head> inline script (runs before CSS paints)
   saved = localStorage['theme']   ('light' | 'dark' | 'auto'; else system)
   dark  = saved=='dark' || (saved!='light' && matchMedia(dark).matches)
   <html>.classList.toggle('dark', dark)   (.dark sets color-scheme in CSS)
        |
        v
 main.css
   @custom-variant dark (&:where(.dark, .dark *));
   :root { light tokens }      .dark { dark tokens }
        ^
        |
 stores/theme.ts  (Pinia setup store)
   mode: 'light'|'dark'|'system'  <- useColorMode({ storageKey: 'theme',
                                       initialValue: 'auto', ... })
   setMode(m)                        maps 'system' <-> vueuse 'auto'
        ^
        |
 components/ThemeToggle.vue -> DropdownMenu + DropdownMenuRadioGroup
```

- **The pre-paint script is inline in `index.html`**, wrapped in `try/catch`
  so blocked storage falls back to system. It must stay tiny and dependency-free;
  it is the only code that runs before Vue. Its storage key and values match
  the store's.
- **`useColorMode`** (already in `@vueuse/core`) handles the class toggle,
  `localStorage`, and the live `matchMedia` listener for `auto`. The store
  wraps it so components follow the "components → stores" rule and tests can
  set the mode directly. vueuse calls it `auto`; the store exposes `system` to
  match the Spanish "Sistema" label and the spec.
- **`color-scheme`** is set on `<html>` with the class, so native scrollbars
  and form controls match the theme.
- **This is the only persisted state.** README and AGENTS.md change from
  "in memory, no localStorage" to "in memory; the theme preference is the only
  value stored in the browser". Research state stays in memory.

Alternatives: keep the media query and override it with
`[data-theme=light]`, which duplicates every dark token block. Or a cookie,
which needs a server; the SPA is static.

### 5. Home page composition

```
 HomeView
  +-- hero         h1 (serif, text-balance) + one-sentence subtitle
  +-- ResearchRequestForm
  |     InputGroup
  |       InputGroupTextarea  (field-sizing-content, max-h-64, overflow-y-auto)
  |       InputGroupAddon align=block-end
  |         Kbd "⌘ ↵" / "Ctrl ↵"   status text (aria-live)   [icon Button  >]
  +-- ExampleQuestions   Button variant="outline" size="sm" rounded chips
  +-- scope grid   Card "Qué investiga" (lucide icons per item)
                   Card "Qué no ofrece"
```

- **The label stays visible** (the spec requires it). It sits above the
  composer as a small muted label, not a placeholder-only design.
- **Submit button.** Icon only (`ArrowUp`), with `aria-label="Enviar"`, which
  keeps the existing test hook and the accessible name.
- **The shortcut hint** picks ⌘ or Ctrl from `navigator.userAgentData?.platform
  ?? navigator.platform` in a tiny `lib/platform.ts` helper, so it is
  testable.
- **Example questions** come from a typed constant in
  `components/ExampleQuestions.vue`. Activating one calls a new store action,
  `applyExample(text)` (not `use…`, which reads as a composable), which sets `question`, clears `validationError`, and
  resets `status` to `idle` unless a request is in flight (a busy request
  keeps its status, so it can't be submitted twice). Focus moves to the field: the form exposes a
  `focus()` method via `defineExpose`, and `HomeView` connects the two
  components through a template ref. Three examples cover rent vs. wages,
  tourist rentals, and public housing, each phrased neutrally.
- **Motion.** The hero, composer, and cards use `motion-safe:animate-in
  motion-safe:fade-in motion-safe:slide-in-from-bottom-2` from
  `tw-animate-css` (already installed), with staggered delays from the
  default scale. Nothing appears only through motion.
- **Background.** A faint dotted grid behind the hero, built with
  `radial-gradient` in `main.css` as a `.bg-paper-grid` utility under
  `@utility`, using `var(--border)`. It lives in `src/styles/`, so it passes
  the lint guard.

### 6. App shell

- Header: `sticky top-0 z-40 border-b bg-background/80 backdrop-blur
  supports-[backdrop-filter]:bg-background/60`. A small lucide `House` mark,
  the name in the serif heading face, and `ThemeToggle` on the right.
- `main` stays `max-w-5xl`. The home hero and composer use `max-w-2xl` and
  are centered.
- `NotFoundView` uses the `Empty` primitive (icon, title, description, link
  styled as `Button variant="outline"` via `as-child`).

### 7. Primitives added with the CLI

Added with `pnpm dlx shadcn-vue@<pinned> add`: `card badge alert kbd separator
skeleton spinner tooltip dropdown-menu input-group empty`. Generated files are
committed as-is. Domain variants are then added to `badge/index.ts` and
`alert/index.ts`. Any generated class with a raw arbitrary literal that
fails `lint:tokens` is replaced with the nearest scale value, never
allow-listed. Primitives not used on any screen yet (Skeleton, Spinner,
Tooltip, source Badge variants) get one unit test each, so they are not
dead weight.

## Risks / Trade-offs

- [Charter missing on Windows and Linux] → The stack falls back to Sitka,
  Cambria, then Georgia, all present on Windows. Linux gets `ui-serif`/`serif`.
  Accepted; revisit with `@fontsource` if it looks poor.
- [A saturated primary fails AA in dark mode] → The dark primary is lighter
  and less saturated (0.75 L). Contrast is checked for every foreground and
  background pair during implementation, and values are recorded in a comment
  in `main.css`.
- [Pre-paint script drifts from the store's key or values] → Both use one
  documented key, `theme`, with stored values `light|dark|auto` (vueuse's
  name for system; anything else reads as system). A unit test reads
  `index.html` and asserts that the key and values appear in the script.
- [jsdom lacks `matchMedia`] → Tests stub `window.matchMedia` in the theme
  store spec.
- [The CLI changes existing `button`/`textarea`] → Run `add` without
  `--overwrite`. Review the diff before accepting any change to existing
  primitives.
- [Moving the form changes existing tests] → Order assertions in the form and
  App specs are updated to the new order (hero → form → scope).

## Migration Plan

Client-only. Users who never pick a theme see the system theme as before.
Rollback means reverting the change; a leftover `theme` key in
`localStorage` is harmless.
