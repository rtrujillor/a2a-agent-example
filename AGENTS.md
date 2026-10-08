# Repository guidance

## Project context

This repository contains an example of an Agent-to-Agent (A2A) application built
with the LangGraph framework. It includes:

- An A2A-compatible agent.
- A client application that communicates with and consumes the agent.
- The configuration required to deploy the agent to an A2A-compatible service,
  such as LiteLLM.

The agent specializes in researching, summarizing, and presenting up-to-date
information about housing-access challenges in Spain. It should provide
balanced, evidence-based answers supported by reliable and recent sources.

When the agent receives a request, it follows this process:

1. Interpret the user's question or instructions and identify the information
   needed.
2. Search the internet using Google Search for relevant and current information.
3. Evaluate the relevance, reliability, publication date, and potential bias of
   the sources.
4. Compare information from multiple sources and identify agreements,
   discrepancies, and uncertainties.
5. Synthesize the findings into a clear response appropriate to the user's
   request.
6. Cite or link to the sources used so the user can verify the information.

The agent should distinguish factual reporting from analysis or inference. When
reliable information is unavailable or conflicting, it should state that
limitation instead of presenting uncertain claims as facts. It should support
research at national, autonomous-community, provincial, and municipal levels
when the user's request calls for that level of geographic detail.

## Working guidelines

- Make focused changes that directly address the requested task.
- Preserve existing behavior and conventions; avoid unrelated changes.
- Add or update tests when introducing behavior, using the project's existing
  test tooling when available.
- Run the relevant tests, lint, and build checks after changing code. If a
  check cannot be run because the project has no corresponding tooling, state
  that clearly rather than adding tooling without need.
- Update documentation when project behavior, setup, or commands change.
- Do not add credentials, secrets, or machine-specific configuration.
-
