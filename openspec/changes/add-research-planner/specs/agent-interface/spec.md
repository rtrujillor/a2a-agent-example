# Spec Delta

## MODIFIED Requirements

### Requirement: Streamed progress
For an accepted message, the agent SHALL first report the task as working,
before any model call. That update carries no text, since the language is not
known yet. The agent SHALL then report each further step as a status update
before the task reaches its final or interrupted state.

#### Scenario: Progress before the outcome
- **WHEN** a client streams a valid in-scope question
- **THEN** it receives the task, then a working update, then the interpretation update, then the plan update, and finally the completed state

#### Scenario: No plan update without a plan
- **WHEN** a client streams a question that is classified as ambiguous or out of scope
- **THEN** it receives no plan update before the task's interrupted or final state

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
- **WHEN** the request is classified as in scope and a valid plan is built
- **THEN** the agent reports a working update that states its interpretation and assumptions, then a working update with the plan, then completes the task with a message saying source search is not available yet

### Requirement: Failures without technical detail
When the language model is unreachable, times out, or returns output that
can't be validated after the bounded retries, including a research plan with
no valid steps, or when the request exceeds the configured total request
time, the agent SHALL end the task as failed. The failure message SHALL be
fixed, in the request's language or else in Spanish. It SHALL NOT include
stack traces, exception text, provider responses, hostnames, or keys.

#### Scenario: Model unreachable
- **WHEN** the model endpoint refuses connections
- **THEN** the task ends as failed with the fixed failure message and no technical detail

#### Scenario: Request time exceeded
- **WHEN** processing exceeds the configured request timeout
- **THEN** the task ends as failed with the fixed failure message

#### Scenario: No valid plan
- **WHEN** the request is in scope but planning yields no valid plan after the bounded retries
- **THEN** the task ends as failed with the fixed failure message, after the interpretation update and without a plan update

#### Scenario: Error is logged for operators
- **WHEN** a task fails
- **THEN** the agent logs the error category and task identifier for operators, without the user's full question or any secret
