import pytest
from pydantic import ValidationError

from housing_access_agent.config import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("MODEL_NAME", "MODEL_API_KEY", "CORS_ALLOWED_ORIGINS", "MAX_CLARIFICATION_ROUNDS"):
        monkeypatch.delenv(name, raising=False)


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "qwen")
    monkeypatch.setenv("MAX_CLARIFICATION_ROUNDS", "3")

    settings = Settings(_env_file=None)

    assert settings.model_name == "qwen"
    assert settings.max_clarification_rounds == 3
    assert settings.a2a_host == "127.0.0.1"


def test_default_clarification_rounds():
    assert Settings(_env_file=None, model_name="m").max_clarification_rounds == 2


def test_origins_are_comma_separated(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "m")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173, http://127.0.0.1:5173 ,")

    settings = Settings(_env_file=None)

    assert settings.cors_allowed_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_wildcard_origin_is_refused():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, model_name="m", cors_allowed_origins="*")


def test_missing_model_name_fails():
    with pytest.raises(ValidationError, match="model_name"):
        Settings(_env_file=None)


def test_negative_clarification_rounds_fail():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, model_name="m", max_clarification_rounds=-1)


def test_secrets_are_hidden_in_repr():
    settings = Settings(
        _env_file=None,
        model_name="m",
        model_api_key="sk-model-secret",
        langfuse_secret_key="lf-secret",
    )

    assert "sk-model-secret" not in repr(settings)
    assert "lf-secret" not in repr(settings)
    assert settings.model_api_key.get_secret_value() == "sk-model-secret"
