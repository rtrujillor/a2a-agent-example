# Spec Delta

## MODIFIED Requirements

### Requirement: Streamed submission
The client SHALL send the question as a single user message with one text
part through the agent's streaming method. Every submission from the question
form SHALL start a new request: it SHALL NOT include a task or context
identifier, even when an earlier request was accepted. Only a reply to the
agent's clarifying question carries identifiers, those of the task it answers,
as `research-progress` defines.

#### Scenario: First submission
- **WHEN** a user submits a valid question
- **THEN** the agent receives one streamed user message whose only part is the trimmed question text, with no task or context identifier

#### Scenario: Later submission starts fresh
- **WHEN** a request was accepted with a context identifier and the user submits a new question
- **THEN** the new message carries no task or context identifier from the earlier request

#### Scenario: Question form during a clarification
- **WHEN** the agent asked a clarifying question and the user submits a new question from the question form instead of replying
- **THEN** the new message carries no task or context identifier
