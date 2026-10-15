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

### Requirement: Theme follows system preference
The web client SHALL render a light theme or a dark theme according to the
operating system's color-scheme preference, and SHALL switch when that
preference changes, without a page reload.

#### Scenario: Dark preference on load
- **WHEN** the app loads and the system prefers a dark color scheme
- **THEN** the dark theme is applied before content is visible to the user

#### Scenario: Preference changes while open
- **WHEN** the system color-scheme preference changes while the app is open
- **THEN** the app switches theme without reloading or losing on-screen content

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
