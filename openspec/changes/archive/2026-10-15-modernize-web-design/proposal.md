# Proposal

## Why

The web client still uses the stock grayscale shadcn-vue palette and reads as
a text document: the one action a visitor comes for, asking a question, sits
below four sections of prose. Most of the research experience (progress,
answer, citations, limitations) is not built yet, so setting a deliberate
visual language now lets every later feature inherit it instead of being
restyled afterwards.

## What Changes

- **Civic/editorial visual identity.** Re-theme the tokens in
  `web/src/styles/main.css` for both themes: warm "paper" and "ink" neutrals,
  a deep civic-blue primary, hairline borders, a smaller radius, and quiet
  entrance motion that runs only when the user has not asked for reduced motion.
- **Editorial typography without web fonts.** Headings use a system serif
  stack (Charter, Iowan Old Style, Georgia) and interface text keeps the system
  sans-serif stack. No font files or font requests are added.
- **Domain tokens.** Add the source-type tokens (official, media, market,
  other) and a limitation-notice token pair, distinct from `destructive`.
- **Ask-first home page.** The question composer moves to the top of the home
  page, under a short title and subtitle. It has a field that grows with its
  content, an icon submit button, and a visible Ctrl/⌘+Enter hint. Example
  questions appear as chips that fill the field without sending. The scope
  ("qué investiga") and exclusions ("qué no ofrece") follow below as cards.
- **Modern app shell.** A sticky, translucent header with the application name
  and a theme control; the not-found page restyled to match.
- **User-selectable theme.** A light/dark/system control in the header. The
  choice persists in the browser, defaults to the system preference, and is
  applied before first paint. **BREAKING** for the current design-system rule
  that the theme follows the OS preference only, using CSS alone.
- **Shared kit for the research view.** Add the shadcn-vue primitives the
  research view will use (Card, Badge with source variants, Alert with notice
  and destructive variants, Kbd, Separator, Skeleton, Spinner, Tooltip,
  DropdownMenu, InputGroup). Streaming progress, the answer, and citations
  are out of scope; they belong to the progress-handling change, which will
  compose this kit.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `web-design-system`: the theme becomes user-selectable (light, dark,
  system) instead of following the system preference only. New requirements
  cover editorial typography and reduced-motion-safe animation.
- `web-app-shell`: the shared layout header gains the theme control and stays
  visible while scrolling; the home page presents its scope and exclusions
  after the question composer.
- `research-request`: the question form moves above the home page content.
  It shows a submit-shortcut hint and offers example questions that fill the
  field without submitting.

## Impact

- **Code (web only):** `src/styles/main.css`, `index.html` (pre-paint theme
  script), `src/App.vue`, `src/views/HomeView.vue`,
  `src/views/NotFoundView.vue`, `src/components/ResearchRequestForm.vue`, new
  `src/components/ThemeToggle.vue`, `src/components/ExampleQuestions.vue`,
  new `src/stores/theme.ts`, new primitives under `src/components/ui/`.
- **Tests:** existing App, form, and store specs updated; new specs for the
  theme store, the theme control, and the example questions.
- **Dependencies:** none new. `@vueuse/core`, `reka-ui`, `@lucide/vue`, and
  `class-variance-authority` are already present; shadcn-vue components are
  vendored source.
- **Docs:** AGENTS.md (web-client theme rule; note that the theme preference
  is the only browser-persisted state) and `web/README.md`. No change to the
  agent, the A2A contract, or the architecture diagrams: everything stays in
  the existing web-client container.
