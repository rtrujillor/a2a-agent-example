# Spec Delta

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Theme follows system preference
**Reason**: Replaced by "User-selectable theme" and "Remembered theme choice",
which keep following the system preference as the default and add explicit
light and dark choices.
**Migration**: No user action needed. Users who never choose a theme see the
same behavior as before. Implementations move the dark theme from a media query
to a class set before first paint.
