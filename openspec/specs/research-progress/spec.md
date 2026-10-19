# research-progress Specification

## Purpose

Lets the user follow an accepted research request in the web client, from
progress and the agent's interpretation to its outcome, and answer the
agent's clarifying question without starting over.

## Requirements

### Requirement: Progress panel
After the agent accepts a request, the home page SHALL show a progress panel
directly below the question form and above the example questions. The panel
SHALL keep reading the agent's stream and add each step as it arrives, in
order. Before the first accepted request the panel SHALL NOT be shown.

#### Scenario: Panel after acceptance
- **WHEN** the agent accepts a request
- **THEN** a progress panel appears between the form and the example questions

#### Scenario: Nothing before a request
- **WHEN** the home page loads and no request has been accepted
- **THEN** no progress panel is shown

### Requirement: Working indicator
While the task is working and no further step has arrived, the panel SHALL
show a Spanish working message with a busy indicator. The indicator SHALL be
removed when the task reaches a final or interrupted state.

#### Scenario: Agent is working
- **WHEN** the agent reports the task as working without a message
- **THEN** the panel shows "Interpretando la pregunta…" with a busy indicator

#### Scenario: Outcome replaces the indicator
- **WHEN** the agent reports a final or interrupted state
- **THEN** the busy indicator is no longer shown

### Requirement: Agent messages as text
Each status update that carries agent text SHALL appear as its own step,
showing the full text with line breaks kept. Agent text SHALL be shown as
plain text and SHALL NOT be interpreted as HTML or Markdown.

#### Scenario: Interpretation with assumptions
- **WHEN** a working update carries "Entendido: alquileres · España · últimos datos disponibles." and a second line of assumptions
- **THEN** the panel shows both lines as separate lines in one step

#### Scenario: Markup is not rendered
- **WHEN** an agent message contains `<b>texto</b>`
- **THEN** the panel shows the characters `<b>texto</b>` literally

### Requirement: Outcome presentation
The panel SHALL present the task's final or interrupted state with the
agent's message and a Spanish heading for that outcome. A completed task
SHALL look neutral. A clarifying question SHALL be prominent but not styled
as an error. A rejected task SHALL use the notice style. A failed task SHALL
use the error style. A state SHALL never be conveyed by color alone.

#### Scenario: Completed
- **WHEN** the task completes with a message
- **THEN** the panel shows the message in a neutral block whose heading names the outcome

#### Scenario: Rejected
- **WHEN** the task is rejected with a reason and a scope note
- **THEN** the panel shows both in the notice style under a heading saying the question can't be researched

#### Scenario: Failed
- **WHEN** the task fails with the agent's fixed message
- **THEN** the panel shows that message in the error style under an error heading

### Requirement: Broken stream
When the stream ends or fails after acceptance but before a final or
interrupted state, the panel SHALL show a fixed Spanish error in the error
style. It SHALL NOT show raw error text or stack traces. The steps already
shown SHALL stay visible, and a new question SHALL be possible.

#### Scenario: Stream drops while working
- **WHEN** the stream closes after the interpretation step and before any outcome
- **THEN** the panel keeps the interpretation, adds the fixed connection-lost error, and the form accepts a new question

### Requirement: Answering a clarifying question
When the task requires input, the clarifying-question block SHALL contain a
labeled Spanish text field and a send button with a Spanish accessible name.
It SHALL also hint that a new question can be written in the main form. The
reply field SHALL follow the question rules: trimmed, rejected before sending
when empty or over 2,000 characters, Ctrl+Enter or Cmd+Enter to send.

#### Scenario: Reply field appears
- **WHEN** the task becomes input-required with a clarifying question
- **THEN** the question block shows the question, a labeled reply field, a send button, and a hint about the main form

#### Scenario: Invalid reply
- **WHEN** the user sends an empty reply
- **THEN** nothing reaches the agent and a Spanish message next to the reply field asks for an answer

### Requirement: Reply continues the task
Sending a valid reply SHALL send one user message with the trimmed reply as
its only text part, on the same task and context identifiers as the
question. The panel SHALL then show the reply as a user step, remove the
reply field, and keep reading the new stream, adding its steps after the
earlier ones.

#### Scenario: Reply and completion
- **WHEN** the user replies "Alquiler en Bilbao" to a clarifying question
- **THEN** the agent receives that text with the task's own identifiers, the panel shows the reply after the question, and then shows the agent's next steps until the outcome

#### Scenario: Second clarifying question
- **WHEN** the agent answers a reply with another clarifying question
- **THEN** a new question block with its own reply field appears after the reply

#### Scenario: Reply cannot be sent
- **WHEN** the agent can't be reached while sending a reply
- **THEN** the reply field keeps the text, shows the fixed connection error, and allows sending again

### Requirement: One request at a time, including replies
While a reply is being sent, its send button SHALL be busy and disabled, and
a second reply SHALL NOT be sent. Submitting a new question from the main
form SHALL close the open stream and clear the panel before the new request
starts.

#### Scenario: New question during a clarification
- **WHEN** the panel shows a clarifying question and the user submits a new question in the main form
- **THEN** the old stream is closed, the panel is cleared, and the new request starts without task or context identifiers

### Requirement: Announced progress
New steps and outcomes SHALL be announced to assistive technology through a
polite live region, without moving keyboard focus.

#### Scenario: Screen reader hears the outcome
- **WHEN** an outcome step is added to the panel
- **THEN** its heading and text sit in a polite live region and focus stays where it was
