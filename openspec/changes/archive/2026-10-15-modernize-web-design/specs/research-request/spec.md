# Spec Delta

## MODIFIED Requirements

### Requirement: Research question form
The home page SHALL show a research question form directly after its title and
one-sentence description, before the detailed scope and exclusions. The form
SHALL have a multi-line text field with a visible Spanish label and a submit
button with a Spanish accessible name. The field SHALL grow with its content up
to a maximum height. The form SHALL accept free text in any language and SHALL
NOT require separate fields for topic, location, or period.

#### Scenario: Form on the home page
- **WHEN** a user opens the root address
- **THEN** the home page shows its title and one-sentence description, followed by a labeled question field and a submit button, followed by the detailed scope and exclusions

#### Scenario: Question in another language
- **WHEN** a user writes the question in English and submits it
- **THEN** the question is sent unchanged, without translation

#### Scenario: Field grows with the question
- **WHEN** the user types a question longer than the field's initial height
- **THEN** the field grows to show the text, up to its maximum height, after which it scrolls

### Requirement: Keyboard submission
The question field SHALL insert a new line on Enter. Ctrl+Enter or Cmd+Enter
in the field SHALL submit the form, the same as activating the submit button.
The form SHALL show a visible hint of this shortcut.

#### Scenario: Enter adds a line
- **WHEN** the user presses Enter in the question field
- **THEN** a new line is inserted and nothing is sent

#### Scenario: Shortcut submits
- **WHEN** the user presses Ctrl+Enter or Cmd+Enter in a field that holds a valid question
- **THEN** the question is submitted

#### Scenario: Shortcut hint
- **WHEN** the home page is shown
- **THEN** the form displays the submit shortcut next to the submit button, using ⌘ on Apple platforms and Ctrl elsewhere

## ADDED Requirements

### Requirement: Example questions
The home page SHALL offer a small set of example research questions in Spanish
as buttons near the question field. Activating an example SHALL replace the
field's text with that question and move focus to the field. It SHALL NOT
submit the question.

#### Scenario: Choosing an example
- **WHEN** the user activates an example question
- **THEN** the question field holds that example's text, the field has focus, and no request reaches the agent

#### Scenario: Example replaces a draft
- **WHEN** the field already holds text and the user activates an example question
- **THEN** the field's text is replaced by the example and any validation message is cleared
