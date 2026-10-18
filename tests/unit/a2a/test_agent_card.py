import json

from a2a.server.request_handlers.response_helpers import agent_card_to_dict

from housing_access_agent.a2a.agent_card import build_agent_card
from housing_access_agent.config import Settings


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        model_name="m",
        model_api_key="sk-model-secret",
        google_search_api_key="google-secret",
        langfuse_public_key="pk-lf-public",
        langfuse_secret_key="sk-lf-secret",
        a2a_agent_url="http://127.0.0.1:8000",
    )


def test_card_fields():
    card = build_agent_card(_settings())

    assert card.name == "Spain Housing Access Agent"
    assert card.description
    assert card.capabilities.streaming is True
    assert list(card.default_input_modes) == ["text/plain"]
    assert list(card.default_output_modes) == ["text/plain"]
    assert len(card.skills) == 1
    assert card.skills[0].id == "housing-access-research"
    assert card.skills[0].examples
    (interface,) = card.supported_interfaces
    assert interface.url == "http://127.0.0.1:8000"
    assert interface.protocol_binding == "JSONRPC"


def test_card_holds_no_secrets():
    serialized = json.dumps(agent_card_to_dict(build_agent_card(_settings())))

    for secret in ("sk-model-secret", "google-secret", "pk-lf-public", "sk-lf-secret"):
        assert secret not in serialized
