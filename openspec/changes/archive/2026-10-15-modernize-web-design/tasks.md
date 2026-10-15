# Tasks

## 1. Primitives

- [x] 1.1 In `web/`, add `card badge alert kbd separator skeleton spinner tooltip dropdown-menu input-group empty` with the pinned shadcn-vue CLI, without `--overwrite`; verify `button` and `textarea` are unchanged in `git diff`, and that `pnpm build` passes
- [x] 1.2 Replace any generated class with a raw arbitrary literal by the nearest scale value; verify `pnpm lint` passes with no new `style-tokens-allow` comments

## 2. Tokens, typography, and variants

- [x] 2.1 Rewrite the light and dark token values in `src/styles/main.css` to the civic/editorial palette (design §1), set `--radius: 0.5rem`, and remove the unused `sidebar-*` tokens; verify `pnpm build` and `pnpm lint` pass
- [x] 2.2 Add `--source-{official,media,market,other}[-foreground]` and `--notice[-foreground]` for both themes and map them with `@theme inline`; verify the utilities (`bg-source-official`, `bg-notice`, ...) compile in `pnpm build`
- [x] 2.3 Check AA contrast for every foreground/background token pair in both themes (4.5:1 text, 3:1 borders, ring, and large text), adjust values until all pass, and record the ratios in a comment block in `main.css`; verify by the recorded table
- [x] 2.4 Set `--font-heading` to the system serif stack (design §3); verify the `Editorial typography` scenarios with a unit test that `h1` carries `font-heading`, and that `pnpm build` output contains no font file
- [x] 2.5 Add the `.bg-paper-grid` utility with `@utility` in `main.css` using only `var(--...)` colors; verify `pnpm lint` passes
- [x] 2.6 Add `official | media | market | other` variants to `ui/badge` and a `notice` variant to `ui/alert`; verify with unit tests that each badge renders its Spanish text label and that `notice` and `destructive` alerts render different classes (`Source-type badges`, `Distinct limitation and error styles`)
- [x] 2.7 Add one smoke unit test each for Skeleton, Spinner, and Tooltip (Tooltip opens on keyboard focus); verify `pnpm test:unit --run` passes

## 3. Theme selection

- [x] 3.1 Switch `main.css` to `@custom-variant dark (&:where(.dark, .dark *))` and move the dark tokens from the media query to `.dark`; verify `pnpm build` passes and no `prefers-color-scheme` rule remains in `main.css`
- [x] 3.2 Add the inline pre-paint script to `index.html` (key `theme`, values `light|dark|system`, `try/catch` fallback to system, sets the `dark` class and `color-scheme`); verify a unit test reads `index.html` and asserts the key and the three values
- [x] 3.3 Create `src/stores/theme.ts` wrapping `useColorMode` (`system` ↔ `auto`); verify unit tests with a stubbed `matchMedia` cover: default system, an explicit choice overriding the system, live switching on system only, persistence of the choice, and an invalid stored value falling back to system
- [x] 3.4 Create `src/components/ThemeToggle.vue` (icon button with `aria-label="Tema"` and a `DropdownMenuRadioGroup` with "Claro", "Oscuro", "Sistema"); verify a unit test opens it by keyboard, selects "Oscuro", and checks that the store mode and the checked item update (`Theme control`)
- [x] 3.5 Update AGENTS.md (web-client theme rule; Pinia in memory, with the theme preference as the only browser-stored value) and `web/README.md` (state section, theme section); verify both files match design §4

## 4. App shell and not-found page

- [x] 4.1 Restyle `App.vue`: a sticky translucent header with the `House` mark, the serif name link, and `ThemeToggle`; verify the existing App specs pass and a new test asserts that the header contains the theme control and the `sticky` class (`Shared layout`)
- [x] 4.2 Rebuild `NotFoundView.vue` with `Empty` and an outline-button link home; verify the router not-found spec still passes (Spanish text, link to `/`, address unchanged)

## 5. Ask-first home page

- [x] 5.1 Add `applyExample(text)` to the research store (sets the question, resets status to idle, clears the validation error); verify with store unit tests, including that no request is sent
- [x] 5.2 Add `src/lib/platform.ts` (Apple-platform detection for the shortcut hint); verify unit tests for macOS and non-macOS platform strings
- [x] 5.3 Rebuild `ResearchRequestForm.vue` on `InputGroup` (visible label, growing textarea with `max-h-64`, `Kbd` shortcut hint, icon submit with `aria-label="Enviar"`, the existing `aria-live` status, and `defineExpose({ focus })`); verify the existing form specs pass, and add tests for the hint (⌘ vs Ctrl) and for the field growing (`field-sizing-content` class present)
- [x] 5.4 Create `src/components/ExampleQuestions.vue` with three neutral Spanish examples as outline chips; verify a unit test that activating one fills the field, focuses it, clears a validation message, and sends nothing (`Example questions`)
- [x] 5.5 Recompose `HomeView.vue`: hero (`bg-paper-grid`, serif `text-balance` title, one-sentence subtitle), the form, the example chips, and a two-card scope grid with lucide icons, with `motion-safe:` entrance classes only; verify a unit test asserts the order hero → form → scope/exclusions and that the exclusions list is present (`Home page at the root address`, `Research question form`)
- [x] 5.6 Verify that every animation class in `src/` is prefixed `motion-safe:` (a unit test that greps the views and components), covering `Reduced-motion-safe animation`

## 6. Integration checks

- [x] 6.1 Run `pnpm test:unit --run`, `pnpm lint`, and `pnpm build` in `web/`, and `pytest` for the agent; report each result, and report any check that is not configured instead of claiming it passed
- [x] 6.2 Run the app with `pnpm dev` and check in a browser: light, dark, and system modes; reload persistence with no flash; the composer, chips, and Ctrl/⌘+Enter; keyboard-only navigation through the header and form; layout at 375 px width with no horizontal scroll

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, which syncs the three spec deltas into `openspec/specs/`.
