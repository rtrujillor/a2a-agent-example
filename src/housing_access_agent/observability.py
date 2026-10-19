"""Logger and optional Langfuse tracing. The agent runs without either backend."""

import logging
import warnings
from typing import Any

from housing_access_agent.config import Settings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


# Client libraries whose DEBUG output would bury the agent's own debug lines.
QUIET_LIBRARIES = ("httpcore", "openai", "langsmith", "urllib3")

# httpx logs every request URL at INFO, and search URLs carry the query.
URL_LOGGING_LIBRARIES = ("httpx",)

# langchain-openai serializes the streamed `parsed` field against a `None` type on every
# structured call; the warning is harmless and would flood the console.
PARSED_SERIALIZER_WARNING = r"(?s)Pydantic serializer warnings:.*field_name='parsed'"


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level.upper(), format=LOG_FORMAT)
    for name in QUIET_LIBRARIES:
        logging.getLogger(name).setLevel(max(logging.INFO, logging.getLogger().level))
    for name in URL_LOGGING_LIBRARIES:
        logging.getLogger(name).setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", message=PARSED_SERIALIZER_WARNING, category=UserWarning)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def langfuse_callbacks(settings: Settings) -> list[Any]:
    """LangChain callbacks that send traces to Langfuse, or [] when not configured."""
    public_key = settings.langfuse_public_key.get_secret_value()
    secret_key = settings.langfuse_secret_key.get_secret_value()
    if not (public_key and secret_key):
        return []

    logger = get_logger(__name__)
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler
    except ImportError as error:
        # Both keys are set, so tracing was wanted: make the gap hard to miss.
        logger.error("Langfuse tracing disabled: the integration could not be imported (%s)", error)
        return []

    Langfuse(public_key=public_key, secret_key=secret_key, host=settings.langfuse_host)
    return [CallbackHandler(public_key=public_key)]
