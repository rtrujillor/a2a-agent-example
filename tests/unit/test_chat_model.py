from housing_access_agent.config import Settings
from housing_access_agent.server import build_chat_model


def _payload(**settings):
    model = build_chat_model(Settings(_env_file=None, model_name="m", **settings))
    return model._get_request_payload([("user", "hola")])


def test_reasoning_effort_is_not_sent_by_default():
    assert "reasoning_effort" not in _payload()


def test_reasoning_effort_is_sent_when_set():
    assert _payload(model_reasoning_effort="none")["reasoning_effort"] == "none"


def test_empty_api_key_uses_placeholder():
    model = build_chat_model(Settings(_env_file=None, model_name="m"))

    assert model.openai_api_key.get_secret_value() == "not-needed"
