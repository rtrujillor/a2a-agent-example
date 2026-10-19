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


def test_streams_with_usage_for_time_to_first_token():
    model = build_chat_model(Settings(_env_file=None, model_name="m", model_base_url="http://127.0.0.1:1234/v1"))

    assert model.streaming is True
    assert model.stream_usage is True
    assert model._should_stream_usage() is True
