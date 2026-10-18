import builtins
import logging

from housing_access_agent.config import Settings
from housing_access_agent.observability import get_logger, langfuse_callbacks


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
    assert "sk-secret" not in caplog.text


def test_logger_needs_no_network():
    logger = get_logger("housing_access_agent.test")

    assert isinstance(logger, logging.Logger)
