# Spec Delta

## Purpose

Lets a user write a housing research question in the web client and send it
to the research agent, ending when the agent has accepted the request.

## ADDED Requirements

### Requirement: Research question form
The home page SHALL show a research question form below its existing content:
a multi-line text field with a visible Spanish label and a submit button with
a Spanish label. The form SHALL accept free text in any language and SHALL NOT
require separate fields for topic, location, or period.

#### Scenario: Form on the home page
- **WHEN** a user opens the root address
- **THEN** the home page shows its existing title and description, followed by a labeled question field and a submit button

#### Scenario: Question in another language
- **WHEN** a user writes the question in English and submits it
- **THEN** the question is sent unchanged, without translation

### Requirement: Keyboard submission
The question field SHALL insert a new line on Enter. Ctrl+Enter or Cmd+Enter
in the field SHALL submit the form, the same as activating the submit button.

#### Scenario: Enter adds a line
- **WHEN** the user presses Enter in the question field
- **THEN** a new line is inserted and nothing is sent

#### Scenario: Shortcut submits
- **WHEN** the user presses Ctrl+Enter or Cmd+Enter in a field that holds a valid question
- **THEN** the question is submitted

### Requirement: Question validation before sending
The client SHALL reject a question that is empty or only whitespace, or that
is longer than 2,000 characters, before any network request. It SHALL show a
Spanish message next to the field naming the problem, and SHALL keep the
user's text.

#### Scenario: Empty question
- **WHEN** the user submits an empty or whitespace-only question
- **THEN** no request reaches the agent and a message asks the user to write a question

#### Scenario: Question too long
- **WHEN** the user submits a question longer than 2,000 characters
- **THEN** no request reaches the agent, a message states the 2,000-character limit, and the text is kept

#### Scenario: Leading and trailing whitespace
- **WHEN** the user submits a valid question surrounded by spaces or blank lines
- **THEN** the question is sent with that surrounding whitespace removed

### Requirement: Agent discovery through the agent card
The client SHALL find the agent's endpoint by reading the agent card at the
configured agent URL. It SHALL NOT hard-code the endpoint, and SHALL NOT send
any credential or secret with the request.

#### Scenario: Endpoint from the card
- **WHEN** a valid question is submitted
- **THEN** the client reads the agent card at the configured agent URL and sends the question to the endpoint the card declares

#### Scenario: No secrets in the request
- **WHEN** a question is sent
- **THEN** the request carries no API key, token, or other secret

### Requirement: Streamed submission
The client SHALL send the question as a single user message with one text
part through the agent's streaming method. Every submission SHALL start a new
request: it SHALL NOT include a task or context identifier, even when an
earlier request was accepted.

#### Scenario: First submission
- **WHEN** a user submits a valid question
- **THEN** the agent receives one streamed user message whose only part is the trimmed question text, with no task or context identifier

#### Scenario: Later submission starts fresh
- **WHEN** a request was accepted with a context identifier and the user submits a new question
- **THEN** the new message carries no task or context identifier from the earlier request

### Requirement: Acceptance of the request
The client SHALL treat the request as accepted when the first stream event
from the agent arrives. It SHALL then keep the task identifier (when the
event has one) and the context identifier, show a Spanish confirmation that
the request was sent, and keep the stream open for progress handling. The
form SHALL keep the submitted question visible.

#### Scenario: Agent accepts the request
- **WHEN** the agent's first stream event for a submitted question carries a task with an identifier and a context identifier
- **THEN** the client keeps both identifiers, shows that the request was sent, and does not close the stream

#### Scenario: Outcome after acceptance is not handled here
- **WHEN** the first stream event already reports the task as rejected, input-required, or failed
- **THEN** the request still counts as accepted, and the outcome is left to progress handling

### Requirement: Connection failure message
When the agent card can't be read or is invalid, the agent can't be reached,
the browser blocks the request, or the stream ends or fails before the first
event, the client SHALL show a fixed Spanish error message in the error style.
It SHALL NOT show raw error text or stack traces, SHALL keep the question, and
SHALL allow another submission.

#### Scenario: Agent unreachable
- **WHEN** a valid question is submitted and the agent URL does not respond
- **THEN** the form shows the fixed connection error message, the question stays in the field, and the submit button is enabled again

#### Scenario: Invalid agent card
- **WHEN** the configured agent URL returns a response that is not a valid agent card
- **THEN** the same fixed connection error message is shown, with no technical detail

#### Scenario: Stream ends before any event
- **WHEN** the agent's stream closes or fails before delivering its first event
- **THEN** the same fixed connection error message is shown and the request is not treated as accepted

### Requirement: One request at a time
While a request is being sent, the client SHALL disable the submit action and
SHALL NOT start a second request. A submission after acceptance SHALL replace
the current request: the client closes the previous stream before starting a
new request.

#### Scenario: Double submit
- **WHEN** the user activates submit twice before the agent responds
- **THEN** only one request reaches the agent

#### Scenario: New question after acceptance
- **WHEN** a request has been accepted and the user submits another valid question
- **THEN** the previous stream is closed and a new request is sent

### Requirement: Announced submission status
Changes to the submission status (sending, sent, validation error, connection
error) SHALL be announced to assistive technology without moving keyboard
focus. The submit control SHALL show a busy state while sending.

#### Scenario: Screen reader hears the result
- **WHEN** a submitted request is accepted or fails
- **THEN** the status message sits in a polite live region and focus stays where it was
