# Spain Housing Access Problem -  A2A Agent


An Agent-to-Agent (A2A) application for researching, summarizing, and presenting
current information about housing-access challenges in Spain.

The project uses LangGraph to coordinate the agent's research workflow and
includes a client for communicating with the agent through the A2A protocol.
The agent is designed for deployment to an A2A-compatible service such as
LiteLLM.

## Purpose

The agent helps users investigate questions about housing access in Spain. It
searches for recent information, assesses the quality of its sources, compares
the findings, and produces a clear, evidence-based response with citations.

Research can cover Spain as a whole or focus on an autonomous community,
province, or municipality.

## Features

- A2A-compatible agent and client.
- LangGraph-based research workflow.
- Internet research through Google Search.
- Evaluation of source relevance, reliability, recency, and potential bias.
- Comparison of multiple sources to identify agreements and discrepancies.
- Clear separation between reported facts, analysis, and inference.
- Responses supported by links to the sources used.
- Support for national, regional, provincial, and municipal research.

## How It Works

When the agent receives a request, it:

1. Interprets the question or instructions.
2. Identifies the information required to answer the request.
3. Searches Google for relevant and current information.
4. Evaluates the quality and potential bias of the available sources.
5. Compares information across multiple sources.
6. Synthesizes the findings into a response suited to the user's request.
7. Includes citations or links so the findings can be verified.

If reliable information is unavailable, incomplete, or conflicting, the agent
should explain the limitation rather than present an uncertain claim as fact.

## Architecture

The project has two primary components:

- **Agent:** Runs the LangGraph workflow, performs research, evaluates sources,
  and prepares the final answer.
- **Client:** Sends A2A requests to the agent and presents its responses.

```text
User -> A2A Client -> A2A Agent -> Google Search
                          |
                          +-> Source evaluation and synthesis
                          |
                          +-> Cited response -> A2A Client -> User
```

### Project Structure

```text
src/
├── a2a_client/                 # Client transport and request handling
└── housing_access_agent/
    ├── a2a/                    # Agent card and A2A execution adapter
    ├── domain/                 # Shared research and evidence types
    ├── tools/                  # Search and official-source adapters
    ├── workflow/               # Classify, plan, research, validate, synthesize
    ├── config.py               # Environment-based configuration
    ├── graph.py                # LangGraph composition root
    ├── observability.py        # Tracing, logging, and quality signals
    ├── prompts.py              # Agent prompts
    ├── server.py               # A2A server entry point
    └── state.py                # Shared workflow state
tests/
├── integration/               # A2A and external-boundary tests
└── unit/                       # Workflow and tool tests
```

## Prerequisites

Before setting up the project, ensure that you have:

- A supported runtime for the agent and client.
- Access to an A2A-compatible service.
- Credentials for the configured Google Search provider.
- Any model-provider credentials required by the deployment environment.

## Configuration

Store configuration in environment variables or a local environment file that
is excluded from version control. Never commit API keys or other credentials.

The configuration reference should document:

- The language-model provider and model.
- Google Search credentials and search-engine settings.
- The agent's host, port, and public A2A endpoint.
- Client connection settings.
- Logging and observability options.

## Installation

1. Clone the repository.
2. Install the agent and client dependencies using the project's package
   manager.
3. Configure the required environment variables.
4. Verify that the configured model and search services are accessible.

## Running the Agent

1. Start the configured A2A-compatible service.
2. Start the agent and expose its A2A endpoint.
3. Confirm that the agent card or discovery endpoint is available.

## Running the Client

1. Configure the client with the agent's A2A endpoint.
2. Start the client.
3. Submit a housing-related question or research instruction.
4. Review the response and its cited sources.

## Example Requests

- What factors are affecting access to rental housing in Madrid?
- Summarize recent changes in residential rental prices in Barcelona.
- Compare housing-access challenges in Valencia and Málaga.
- What public housing measures have recently been announced in Spain?
- Explain the available evidence about short-term rentals and local housing
  supply in a specific municipality.

## Deployment

The agent is intended to run on an A2A-compatible service such as LiteLLM. A
deployment should provide:

- Secure secret and configuration management.
- HTTPS for public endpoints.
- Authentication and authorization where appropriate.
- Request timeouts and rate limits for external services.
- Logging, tracing, and error monitoring.
- A documented health-check mechanism.

## Source and Response Guidelines

Agent responses should:

- Prefer authoritative, recent, and directly relevant sources.
- Use multiple independent sources where practical.
- Consider publication date, methodology, and potential bias.
- Distinguish facts from interpretation or inference.
- Identify material disagreements or uncertainty.
- Link to the sources supporting the response.
- Avoid overstating conclusions when the evidence is limited.

## Development

Keep changes focused and preserve established project conventions. When adding
behavior:

- Add or update relevant tests.
- Run the available test, lint, and build checks.
- Update this README when setup, configuration, commands, or behavior changes.
- Do not add secrets or machine-specific configuration.

## Testing

Tests should cover the agent workflow, client communication, source handling,
error cases, and A2A protocol behavior. Integration tests that access external
services should use safe test credentials or documented mocks.

## Contributing

Before submitting a change:

1. Keep the change limited to a clear purpose.
2. Add tests for new or modified behavior.
3. Run the relevant project checks.
4. Update documentation affected by the change.
5. Confirm that no credentials or private data are included.

## License

Add the project's license information here.
