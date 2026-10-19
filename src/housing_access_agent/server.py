"""Application entry point for serving the agent over A2A."""

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
from housing_access_agent.graph import build_graph
from housing_access_agent.observability import configure_logging, langfuse_callbacks
from housing_access_agent.workflow.classifier import make_classifier
from housing_access_agent.workflow.planner import make_planner

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
        **options,
    )


def create_app(settings: Settings, model: BaseChatModel) -> Starlette:
    graph = build_graph(make_classifier(model, settings), make_planner(model, settings), InMemorySaver())
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
    return Starlette(routes=routes, middleware=middleware)


def main() -> None:
    import uvicorn

    settings = Settings()
    configure_logging(settings)
    app = create_app(settings, build_chat_model(settings))
    uvicorn.run(app, host=settings.a2a_host, port=settings.a2a_port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
