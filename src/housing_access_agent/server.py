"""Application entry point for serving the agent over A2A."""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.utils.constants import DEFAULT_RPC_URL
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from housing_access_agent.a2a.agent_card import build_agent_card
from housing_access_agent.a2a.executor import HousingAgentExecutor
from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import ToolName
from housing_access_agent.graph import build_graph
from housing_access_agent.observability import configure_logging, langfuse_callbacks
from housing_access_agent.tools.base import SearchTool
from housing_access_agent.tools.brave_search import BraveSearchTool
from housing_access_agent.workflow.classifier import make_classifier
from housing_access_agent.workflow.planner import make_planner
from housing_access_agent.workflow.researcher import make_researcher

logger = logging.getLogger(__name__)

# LM Studio ignores the key, but the OpenAI client refuses an empty one.
PLACEHOLDER_API_KEY = "not-needed"


def build_chat_model(settings: Settings) -> ChatOpenAI:
    options = {}
    if effort := settings.model_reasoning_effort.strip():
        options["reasoning_effort"] = effort
    return ChatOpenAI(
        base_url=settings.model_base_url,
        model=settings.model_name,
        api_key=settings.model_api_key.get_secret_value() or PLACEHOLDER_API_KEY,
        timeout=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
        temperature=0,
        # Streaming gives Langfuse the time to first token; usage then comes on the last chunk,
        # which langchain-openai only requests by default for OpenAI's own URL.
        streaming=True,
        stream_usage=True,
        **options,
    )


def create_app(settings: Settings, model: BaseChatModel, search_tool: SearchTool | None = None) -> Starlette:
    """Wire the agent. Without a search tool, Brave Search is used over a client closed on shutdown."""
    http_client: httpx.AsyncClient | None = None
    if search_tool is None:
        http_client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
        search_tool = BraveSearchTool(http_client, settings.brave_search_api_key.get_secret_value(), settings)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        yield
        if http_client is not None:
            await http_client.aclose()

    graph = build_graph(
        make_classifier(model, settings),
        make_planner(model, settings),
        make_researcher({ToolName.WEB_SEARCH: search_tool}, settings),
        InMemorySaver(),
    )
    executor = HousingAgentExecutor(graph, settings, callbacks=langfuse_callbacks(settings))
    card = build_agent_card(settings)
    handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore(), agent_card=card)
    routes = create_agent_card_routes(card) + create_jsonrpc_routes(handler, DEFAULT_RPC_URL)
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["content-type", "a2a-version", "a2a-extensions"],
        )
    ]
    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


def missing_settings(settings: Settings) -> list[str]:
    """Environment variables the server needs but that are empty."""
    return [] if settings.brave_search_api_key.get_secret_value().strip() else ["BRAVE_SEARCH_API_KEY"]


def main() -> None:
    import uvicorn

    settings = Settings()
    configure_logging(settings)
    if missing := missing_settings(settings):
        logger.error("%s is required; set it in the environment or .env", ", ".join(missing))
        sys.exit(1)
    app = create_app(settings, build_chat_model(settings))
    uvicorn.run(app, host=settings.a2a_host, port=settings.a2a_port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
