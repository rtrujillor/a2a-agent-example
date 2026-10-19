# agent-interface Specification

## Purpose

Defines how the research agent publishes itself over A2A, accepts research
tasks, and reports their progress and outcomes to clients as task states and
messages.

## Requirements

### Requirement: Agent card
The agent SHALL serve an agent card at the standard well-known path of its
configured public URL. The card SHALL name the agent, describe it, declare
one housing-research skill with example questions, declare streaming
support, and declare text as its only input and output mode. It SHALL NOT
contain any secret.

#### Scenario: Card is served
- **WHEN** a client requests the agent card at the well-known path
- **THEN** it receives a valid card with the agent's name, description, one research skill, streaming enabled, the JSON-RPC endpoint URL, and text input and output modes

#### Scenario: No secrets in the card
- **WHEN** the agent runs with a model key and Langfuse keys configured
- **THEN** none of those values appears anywhere in the card

### Requirement: Local binding and CORS
The agent SHALL bind to the configured host, `127.0.0.1` by default. It
SHALL allow cross-origin requests only from the configured client origins,
and SHALL NOT allow every origin.

#### Scenario: Configured origin
- **WHEN** a browser at a configured client origin sends a preflight or a request to the card or the endpoint
- **THEN** the response allows that origin

#### Scenario: Other origin
- **WHEN** a request comes from an origin that is not configured
- **THEN** the response carries no header allowing that origin, and no response allows every origin

### Requirement: Message intake limits
Before any model call, the agent SHALL check that a message has exactly one
part, that the part is text with a plain-text or unspecified media type, and
that the trimmed text is between 1 and 2,000 characters. A message that fails
any check SHALL end its task as rejected with a short message stating what
was wrong, in Spanish, since the language is not known before
classification.

#### Scenario: Valid message
- **WHEN** a message has one plain-text part with 1 to 2,000 characters after trimming
- **THEN** the agent starts working on it

#### Scenario: Too long
- **WHEN** a message's text is longer than 2,000 characters after trimming
- **THEN** the task ends as rejected with a message naming the 2,000-character limit, and the model is not called

#### Scenario: Unsupported content
- **WHEN** a message has a file or data part, more than one part, or a non-text media type
- **THEN** the task ends as rejected with a message saying only one text question is accepted, and the model is not called

#### Scenario: Empty text
- **WHEN** a message's text is empty or whitespace only
- **THEN** the task ends as rejected with a message asking for a question, and the model is not called

### Requirement: New tasks from empty identifiers
The agent SHALL treat a message without a task identifier or context
identifier, or with empty ones, as a new request. It SHALL then assign new
identifiers, so separate requests never share conversation memory.

#### Scenario: Empty identifiers
- **WHEN** two messages arrive with empty task and context identifiers
- **THEN** each becomes its own task with its own new task and context identifiers

### Requirement: Streamed progress
For an accepted message, the agent SHALL first report the task as working,
before any model call. That update carries no text, since the language is not
known yet. The agent SHALL then report each further step as a status update
before the task reaches its final or interrupted state.

#### Scenario: Progress before the outcome
- **WHEN** a client streams a valid in-scope question
- **THEN** it receives the task, then a working update, then the interpretation update, and finally the completed state

### Requirement: Outcome to task state
The agent SHALL map each workflow outcome to one A2A task state. An
out-of-scope request ends as rejected, an ambiguous request as
input-required, and an in-scope request as completed. Each SHALL carry an
agent message in the request's language that explains the outcome.

#### Scenario: Out of scope
- **WHEN** the request is classified as out of scope
- **THEN** the task ends as rejected with a message explaining why it can't be researched and what the agent covers

#### Scenario: Ambiguous
- **WHEN** the request is classified as ambiguous
- **THEN** the task becomes input-required with a message holding one clarifying question

#### Scenario: In scope, before research exists
- **WHEN** the request is classified as in scope
- **THEN** the agent reports a working update that states its interpretation and assumptions, then completes the task with a message saying research is not available yet

### Requirement: Continuing an input-required task
When a message arrives for a task in the input-required state, with the same
task and context identifiers, the agent SHALL interpret it together with the
earlier messages of that task, not on its own. Messages SHALL NOT be shared
across different context identifiers.

#### Scenario: Clarification resolves the request
- **WHEN** a task is input-required after "¿Y los precios?" and the user replies "Alquiler en Bilbao" on the same task
- **THEN** the agent interprets both messages together and continues as for an in-scope request

#### Scenario: Separate contexts stay separate
- **WHEN** a new request starts without identifiers while another task is input-required
- **THEN** the new request is interpreted only from its own message

### Requirement: Failures without technical detail
When the language model is unreachable, times out, or returns output that
can't be validated after the bounded retries, or when the request exceeds the
configured total request time, the agent SHALL end the task as failed. The
failure message SHALL be fixed, in the request's language or else in Spanish.
It SHALL NOT include stack traces, exception text, provider responses,
hostnames, or keys.

#### Scenario: Model unreachable
- **WHEN** the model endpoint refuses connections
- **THEN** the task ends as failed with the fixed failure message and no technical detail

#### Scenario: Request time exceeded
- **WHEN** processing exceeds the configured request timeout
- **THEN** the task ends as failed with the fixed failure message

#### Scenario: Error is logged for operators
- **WHEN** a task fails
- **THEN** the agent logs the error category and task identifier for operators, without the user's full question or any secret
