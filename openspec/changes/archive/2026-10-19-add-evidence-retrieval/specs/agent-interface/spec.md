# Spec Delta

## MODIFIED Requirements

### Requirement: Streamed progress
For an accepted message, the agent SHALL first report the task as working,
before any model call. That update carries no text, since the language is not
known yet. The agent SHALL then report each further step as a status update
before the task reaches its final or interrupted state.

#### Scenario: Progress before the outcome
- **WHEN** a client streams a valid in-scope question whose plan has three steps
- **THEN** it receives the task, then a working update, then the interpretation update, then the plan update, then one search update per step in the plan's order, and finally the completed state

#### Scenario: No plan update without a plan
- **WHEN** a client streams a question that is classified as ambiguous or out of scope
- **THEN** it receives no plan update and no search update before the task's interrupted or final state

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
- **WHEN** the request is classified as in scope, a valid plan is built, and at least one search returns results
- **THEN** the agent reports the interpretation, the plan, and each search, then completes the task with the sources summary

### Requirement: Failures without technical detail
When the language model is unreachable, times out, or returns output that
can't be validated after the bounded retries, including a research plan with
no valid steps, or when no search of the plan returns any result, or when
the request exceeds the configured total request time, the agent SHALL end
the task as failed. The failure message SHALL be fixed, in the request's
language or else in Spanish. It SHALL NOT include stack traces, exception
text, provider responses, hostnames, or keys.

#### Scenario: Model unreachable
- **WHEN** the model endpoint refuses connections
- **THEN** the task ends as failed with the fixed failure message and no technical detail

#### Scenario: Request time exceeded
- **WHEN** processing exceeds the configured request timeout
- **THEN** the task ends as failed with the fixed failure message

#### Scenario: No valid plan
- **WHEN** the request is in scope but planning yields no valid plan after the bounded retries
- **THEN** the task ends as failed with the fixed failure message, after the interpretation update and without a plan update

#### Scenario: No search results
- **WHEN** every search of the plan fails or returns no result
- **THEN** the task ends as failed with the fixed failure message, after the search updates, and without the search provider's error text

#### Scenario: Error is logged for operators
- **WHEN** a task fails
- **THEN** the agent logs the error category and task identifier for operators, without the user's full question or any secret

## ADDED Requirements

### Requirement: Search update
After each search, the agent SHALL report a working update in the request's
language. It SHALL give the step's number and the plan's step count, the
step's sub-question and source kind, and the number of sources kept, or say
that the search found nothing or failed. Queries, domains, URLs, and
provider errors SHALL NOT be shown.

#### Scenario: Search with results
- **WHEN** the second of four Spanish steps, an official one, keeps 3 sources
- **THEN** the update names search 2 of 4, the sub-question, official sources, and 3 sources, with no query or domain

#### Scenario: Failed search
- **WHEN** a search fails after its retries
- **THEN** its update says the search could not be completed, with no error detail, and the next search update follows

### Requirement: Sources summary
When research ends with evidence, the completed task's message SHALL give,
in the request's language, the number of sources found by source type, the
number of searches without results, and a note that source validation and
the written answer are not available yet. Market sources SHALL be labelled
as offer prices.

#### Scenario: Mixed sources
- **WHEN** research keeps 4 official, 3 media, and 2 market sources, and one search found nothing
- **THEN** the completed message gives 9 sources, split as 4 official, 3 media, and 2 portal offer prices, says 1 search had no results, and says validation and the answer are not available yet
