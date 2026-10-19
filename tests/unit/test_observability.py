import builtins
import logging
import warnings

from housing_access_agent.config import Settings
from housing_access_agent.observability import configure_logging, get_logger, langfuse_callbacks


def test_no_keys_means_no_callbacks():
    assert langfuse_callbacks(Settings(_env_file=None, model_name="m")) == []


def test_one_key_is_not_enough():
    settings = Settings(_env_file=None, model_name="m", langfuse_public_key="pk")

    assert langfuse_callbacks(settings) == []


def test_missing_integration_disables_tracing(monkeypatch, caplog):
    real_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name.startswith("langfuse"):
            raise ImportError("langfuse integration unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failing_import)
    settings = Settings(_env_file=None, model_name="m", langfuse_public_key="pk", langfuse_secret_key="sk-secret")

    assert langfuse_callbacks(settings) == []
    assert "tracing disabled" in caplog.text
    assert caplog.records[-1].levelno == logging.ERROR
    assert "sk-secret" not in caplog.text


def test_both_keys_give_a_langfuse_handler():
    # Building the client and handler sends nothing until traces are flushed.
    from langfuse.langchain import CallbackHandler

    settings = Settings(
        _env_file=None,
        model_name="m",
        langfuse_host="http://127.0.0.1:9",
        langfuse_public_key="pk-test",
        langfuse_secret_key="sk-test",
    )

    callbacks = langfuse_callbacks(settings)

    assert len(callbacks) == 1
    assert isinstance(callbacks[0], CallbackHandler)


def test_logger_needs_no_network():
    logger = get_logger("housing_access_agent.test")

    assert isinstance(logger, logging.Logger)


def test_only_the_parsed_serializer_warning_is_silenced():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        configure_logging(Settings(_env_file=None, model_name="m"))
        warnings.warn(
            "Pydantic serializer warnings:\n  PydanticSerializationUnexpectedValue(Expected `none` "
            "[field_name='parsed', input_value=Answer(), input_type=Answer])",
            UserWarning,
        )
        warnings.warn("Pydantic serializer warnings:\n  something else", UserWarning)

    assert [str(w.message) for w in caught] == ["Pydantic serializer warnings:\n  something else"]


def test_httpx_request_urls_are_not_logged_at_info():
    configure_logging(Settings(_env_file=None, model_name="m", log_level="DEBUG"))

    assert logging.getLogger("httpx").level == logging.WARNING
