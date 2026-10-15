# web-app-shell Specification

## Purpose

Defines the web client's page structure: a home page where users start, URL
navigation between pages, and clear handling of addresses that do not exist.

## Requirements

### Requirement: Home page at the root address
The web client SHALL show the home page at the root address (`/`). The home
page SHALL present the application title, a short description of what the
agent researches about housing access in Spain, and what it does not provide
(personalized legal or financial advice, property valuations, investment
recommendations, forecasts). The title and a one-sentence description SHALL
precede the research question form; the detailed scope and exclusions SHALL
follow it. The home page text SHALL be in Spanish.

#### Scenario: Opening the app
- **WHEN** a user opens the root address
- **THEN** the home page shows the application title, the description of what the agent researches, and the list of what it does not provide

#### Scenario: Question form comes first
- **WHEN** a user opens the root address
- **THEN** the title and one-sentence description appear before the research question form, and the detailed scope and exclusions appear after it

### Requirement: Shared layout
Every page SHALL render inside a shared layout whose header shows the
application name and links to the home page. The header SHALL contain the
theme control and SHALL stay visible at the top of the viewport while the page
scrolls.

#### Scenario: Returning home from the header
- **WHEN** a user on any page activates the application name in the header
- **THEN** the home page is shown and the address is `/`

#### Scenario: Header stays visible
- **WHEN** a user scrolls down a page taller than the viewport
- **THEN** the header with the application name and the theme control remains visible at the top

### Requirement: Theme control
The header SHALL provide a theme control with a Spanish accessible name that
offers three labeled choices in Spanish: light ("Claro"), dark ("Oscuro"), and
system ("Sistema"). The control SHALL indicate the current choice and SHALL be
operable by keyboard.

#### Scenario: Choosing a theme by keyboard
- **WHEN** a keyboard user focuses the theme control, opens it, and selects "Oscuro"
- **THEN** the dark theme is applied and the control indicates "Oscuro" as the current choice

#### Scenario: Control is announced
- **WHEN** a screen reader reaches the theme control
- **THEN** it announces the control's Spanish name and, when opened, the three choices with the current one marked as selected

### Requirement: Addressable pages
Each page SHALL have its own URL path without a hash fragment. Loading that
URL directly or reloading it SHALL show the same page, and the browser's back
and forward buttons SHALL move between visited pages.

#### Scenario: Direct load of a page URL
- **WHEN** a user loads a page's URL directly in a new browser tab
- **THEN** that page is shown, not the home page or an error from the server

#### Scenario: Back button
- **WHEN** a user navigates from the home page to another page and presses the browser's back button
- **THEN** the home page is shown again and the address is `/`

### Requirement: Not-found page
Any address that matches no page SHALL show a not-found page in Spanish that
says the page does not exist and links to the home page. The address SHALL
stay as entered.

#### Scenario: Unknown address
- **WHEN** a user opens an address that matches no page, such as `/no-existe`
- **THEN** the not-found page is shown, the address still reads `/no-existe`, and a link leads to the home page

### Requirement: Document language and title
The web page SHALL declare Spanish as its document language and SHALL have a
descriptive document title instead of a framework placeholder.

#### Scenario: Browser tab and assistive technology
- **WHEN** the app is loaded
- **THEN** the document language is `es` and the browser tab shows the application title
