# web-design-system Specification

## Purpose

Gives the web client one source of visual design decisions (tokens, themes,
and shared component styles), so the interface stays consistent, accessible,
and changeable from a single place.

## Requirements

### Requirement: Central design tokens
The web client SHALL define all colors, radii, and typography as named design
tokens in a single stylesheet. Components SHALL obtain these values only
through the tokens.

#### Scenario: Token change propagates
- **WHEN** the value of a semantic token (for example, the primary color) is changed in the central stylesheet
- **THEN** every component that uses that token shows the new value without any change to component files

### Requirement: No raw style values in components
Component files SHALL NOT contain raw color literals or arbitrary one-off style
values. The web client's lint check MUST fail when they do.

#### Scenario: Raw color rejected
- **WHEN** a component file contains a hexadecimal color or an arbitrary color value in a class
- **THEN** the lint check fails and names the file and line

#### Scenario: Token usage accepted
- **WHEN** a component styles itself only through token-based classes or variables
- **THEN** the lint check passes

### Requirement: User-selectable theme
The web client SHALL offer three theme choices: light, dark, and system. With
system, it SHALL follow the operating system's color-scheme preference and
switch live when that preference changes, without a reload. System SHALL be
the default when no choice has been made.

#### Scenario: Default follows the system
- **WHEN** a user who has never chosen a theme opens the app while the system prefers a dark color scheme
- **THEN** the dark theme is applied

#### Scenario: Explicit choice overrides the system
- **WHEN** the user chooses the light theme while the system prefers a dark color scheme
- **THEN** the light theme is applied immediately, without a reload or loss of on-screen content

#### Scenario: System preference changes while on system
- **WHEN** the theme choice is system and the system color-scheme preference changes while the app is open
- **THEN** the app switches theme without reloading or losing on-screen content

#### Scenario: System preference changes while on an explicit choice
- **WHEN** the theme choice is dark and the system color-scheme preference changes to light
- **THEN** the app stays in the dark theme

### Requirement: Remembered theme choice
The web client SHALL remember the user's theme choice in the browser across
reloads and SHALL apply it before content is visible, so the wrong theme never
flashes. The theme choice SHALL be the only state the web client keeps in the
browser. If the stored choice is unavailable or invalid, the client SHALL use
system.

#### Scenario: Choice survives a reload
- **WHEN** the user chooses the dark theme and reloads the page
- **THEN** the dark theme is applied before content is visible

#### Scenario: Browser storage unavailable
- **WHEN** browser storage cannot be read or holds an unrecognized value
- **THEN** the app uses the system choice and shows no error

### Requirement: Accessible contrast
Text and essential interface elements SHALL meet WCAG 2.2 AA contrast in both
themes: 4.5:1 for normal text, 3:1 for large text, focus indicators, and
component boundaries.

#### Scenario: Body text contrast
- **WHEN** body text is measured against its background in the light theme and in the dark theme
- **THEN** the contrast ratio is at least 4.5:1 in each

### Requirement: Source-type badges
The web client SHALL provide one badge style per source type: official, media,
market, and other. Each badge SHALL show a text label, so the type is not
conveyed by color alone.

#### Scenario: Consistent badge per type
- **WHEN** two citations of the same source type are displayed anywhere in the app
- **THEN** both use the same badge appearance and label

#### Scenario: Type readable without color
- **WHEN** a citation badge is viewed in grayscale or by a screen reader
- **THEN** the source type is still identifiable from its text label

### Requirement: Distinct limitation and error styles
The web client SHALL style limitation notices (uncertainty, missing data)
visibly differently from error messages (failed requests).

#### Scenario: Limitation is not shown as an error
- **WHEN** an answer includes a limitation notice and no error occurred
- **THEN** the notice uses the limitation style, not the error style

### Requirement: Keyboard-accessible shared components
Shared interactive components (buttons, selects, text areas, tooltips) SHALL
be operable by keyboard and SHALL show a visible focus indicator that uses the
focus token.

#### Scenario: Keyboard navigation
- **WHEN** a user moves through the interface with Tab and activates controls with Enter or Space
- **THEN** every shared interactive component can be reached and operated, and the focused element shows a visible focus ring

### Requirement: Editorial typography
The web client SHALL set headings in a serif typeface and interface and body
text in a sans-serif typeface, both defined as tokens. It SHALL use only fonts
installed on the user's system and SHALL NOT download font files.

#### Scenario: Heading and body typefaces
- **WHEN** a page with a heading and body text is rendered
- **THEN** the heading uses the serif heading token and the body text uses the sans-serif token

#### Scenario: No font downloads
- **WHEN** the app loads
- **THEN** no font file is requested from any server

### Requirement: Reduced-motion-safe animation
Decorative motion (entrance transitions, pulsing indicators) SHALL run only
when the user has not requested reduced motion. No information SHALL be
conveyed by motion alone.

#### Scenario: Reduced motion requested
- **WHEN** the system requests reduced motion and the home page loads
- **THEN** content appears without entrance animation
