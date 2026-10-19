import logging

import pytest
import uvicorn

from housing_access_agent import server
from housing_access_agent.config import Settings


@pytest.fixture
def env(monkeypatch, tmp_path):
    # No .env in the working directory, so only these variables apply.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_NAME", "m")
    monkeypatch.setenv("MODEL_API_KEY", "sk-model-secret")
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    started = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: started.append(True))
    return monkeypatch, started


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_search_key_stops_startup(env, caplog, value):
    monkeypatch, started = env
    if value is not None:
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", value)

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as exited:
        server.main()

    assert exited.value.code == 1
    assert started == []
    assert "BRAVE_SEARCH_API_KEY" in caplog.text
    assert "sk-model-secret" not in caplog.text


def test_search_key_lets_the_server_start(env):
    monkeypatch, started = env
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-secret")

    server.main()

    assert started == [True]


def test_missing_settings():
    assert server.missing_settings(Settings(_env_file=None, model_name="m")) == ["BRAVE_SEARCH_API_KEY"]
    assert server.missing_settings(Settings(_env_file=None, model_name="m", brave_search_api_key="k")) == []
