"""The A2A server in process, with a fake chat model and search tool. No network access."""

import asyncio
import json
import uuid

import httpx
import pytest

from housing_access_agent.config import Settings
from housing_access_agent.server import create_app
from tests.fakes import (
    FakeSearchTool,
    FakeStructuredChatModel,
    ambiguous,
    classification,
    media_step,
    plan,
    plan_step,
    source,
)

ORIGIN = "http://localhost:5173"
FIXED_FAILURE = "No se ha podido procesar la solicitud. Inténtalo de nuevo más tarde."


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        model_name="fake",
        model_api_key="sk-integration-secret",
        cors_allowed_origins=ORIGIN,
        **overrides,
    )


def _client(script, searches=None, **settings):
    model = FakeStructuredChatModel(script=list(script))
    tool = FakeSearchTool(searches, numbered=searches is None)
    app = create_app(_settings(**settings), model, tool)
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000")
    client.search_tool = tool
    return client, model


def _message(text, task_id="", context_id="", parts=None):
    return {
        "messageId": str(uuid.uuid4()),
        "role": "ROLE_USER",
        "parts": parts if parts is not None else [{"text": text, "mediaType": "text/plain"}],
        "taskId": task_id,
        "contextId": context_id,
    }


async def _stream(client, message):
    body = {"jsonrpc": "2.0", "id": 1, "method": "SendStreamingMessage", "params": {"message": message}}
    response = await client.post("/", json=body, headers={"A2A-Version": "1.0", "Origin": ORIGIN})
    assert response.status_code == 200
    events = []
    for line in response.text.splitlines():
        if line.startswith("data:"):
            payload = json.loads(line.removeprefix("data:").strip())
            assert "error" not in payload, payload
            events.append(payload["result"])
    return events


def _states(events):
    states = []
    for event in events:
        if "task" in event:
            states.append((event["task"]["status"]["state"], ""))
        elif "statusUpdate" in event:
            status = event["statusUpdate"]["status"]
            text = "".join(part.get("text", "") for part in status.get("message", {}).get("parts", []))
            states.append((status["state"], text))
    return states


def _ids(events):
    first = events[0]["task"]
    return first["id"], first["contextId"]


async def test_agent_card_is_served():
    client, _ = _client([])
    async with client:
        response = await client.get("/.well-known/agent-card.json")

    card = response.json()
    assert response.status_code == 200
    assert card["name"] == "Spain Housing Access Agent"
    assert card["capabilities"]["streaming"] is True
    assert card["supportedInterfaces"][0]["url"] == "http://127.0.0.1:8000"
    assert "sk-integration-secret" not in response.text


@pytest.mark.parametrize("path", ["/", "/.well-known/agent-card.json"])
async def test_cors_allows_only_the_configured_origin(path):
    client, _ = _client([])
    headers = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,a2a-version"}
    async with client:
        allowed = await client.options(path, headers={"Origin": ORIGIN, **headers})
        other = await client.options(path, headers={"Origin": "http://evil.example", **headers})

    assert allowed.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-origin" not in other.headers
    assert allowed.headers["access-control-allow-origin"] != "*"


async def test_in_scope_streams_progress_and_completes():
    client, _ = _client([classification(location=None, period=None), plan(plan_step(), media_step())])
    async with client:
        events = await _stream(client, _message("¿Cómo están los alquileres?"))

    states = _states(events)
    assert [state for state, _ in states] == [
        "TASK_STATE_SUBMITTED",
        "TASK_STATE_WORKING",
        "TASK_STATE_WORKING",
        "TASK_STATE_WORKING",
        "TASK_STATE_WORKING",
        "TASK_STATE_WORKING",
        "TASK_STATE_COMPLETED",
    ]
    assert states[2][1].startswith("Entendido: alquileres · España · últimos datos disponibles.")
    assert "se considera España en su conjunto" in states[2][1]
    assert states[3][1].splitlines() == [
        "Plan de investigación (2 búsquedas):",
        "- ¿Cuál es el alquiler medio en Madrid? · fuentes oficiales",
        "- ¿Qué se ha publicado recientemente? · medios",
    ]
    assert states[4][1] == (
        "Búsqueda 1/2 · fuentes oficiales: ¿Cuál es el alquiler medio en Madrid?\nFuentes encontradas: 1."
    )
    assert states[5][1].startswith("Búsqueda 2/2 · medios: ¿Qué se ha publicado recientemente?")
    assert states[6][1].startswith("Fuentes encontradas: 2 (oficiales: 2).")
    assert "aún no están disponibles" in states[6][1]
    assert len(client.search_tool.queries) == 2


async def test_official_step_keeps_only_its_sites():
    searches = [[source("https://example-blog.com/x"), source("https://www.ine.es/ipva")], [source("https://elpais.com/a")]]
    client, _ = _client([classification(), plan(plan_step(), media_step())], searches)
    async with client:
        events = await _stream(client, _message("Alquileres en Madrid"))

    states = _states(events)
    assert states[-1][0] == "TASK_STATE_COMPLETED"
    assert states[-1][1].startswith("Fuentes encontradas: 2 (oficiales: 1 · medios: 1).")
    assert client.search_tool.queries[0].sites == ["ine.es"]


async def test_every_search_empty_fails_after_search_updates():
    client, _ = _client([classification(), plan(plan_step(), media_step())], [[], []])
    async with client:
        events = await _stream(client, _message("Alquileres en Madrid"))

    states = _states(events)
    assert states[-1] == ("TASK_STATE_FAILED", FIXED_FAILURE)
    assert states[-2][1].startswith("Búsqueda 2/2") and states[-2][1].endswith("Sin resultados.")
    assert states[-3][1].startswith("Búsqueda 1/2")


async def test_failed_search_is_reported_without_detail():
    from housing_access_agent.tools.base import SearchErrorCategory, SearchToolError

    searches = [SearchToolError(SearchErrorCategory.REJECTED), [source("https://elpais.com/a")]]
    client, _ = _client([classification(), plan(plan_step(), media_step())], searches)
    async with client:
        events = await _stream(client, _message("Alquileres en Madrid"))

    states = _states(events)
    assert states[4][1].endswith("No se ha podido completar la búsqueda.")
    assert "rejected" not in states[4][1]
    assert states[-1][0] == "TASK_STATE_COMPLETED"
    assert "Búsquedas sin resultados: 1." in states[-1][1]


async def test_out_of_scope_is_rejected():
    client, _ = _client([classification(verdict="out_of_scope", reason="No es una pregunta sobre vivienda.", topic=None)])
    async with client:
        events = await _stream(client, _message("¿Quién ganó la liga?"))

    state, text = _states(events)[-1]
    assert state == "TASK_STATE_REJECTED"
    assert text.startswith("No es una pregunta sobre vivienda.")
    assert not any(text.startswith("Plan de investigación") for _, text in _states(events))


async def test_ambiguous_then_reply_on_the_same_task_completes():
    client, model = _client(
        [ambiguous(), classification(location={"name": "Bilbao", "level": "municipality"}, period=None), plan()]
    )
    async with client:
        first = await _stream(client, _message("¿Y los precios?"))
        task_id, context_id = _ids(first)
        second = await _stream(client, _message("Alquiler en Bilbao", task_id, context_id))

    assert _states(first)[-1] == ("TASK_STATE_INPUT_REQUIRED", ambiguous()["clarifying_question"])
    assert not any(text.startswith("Plan de investigación") for _, text in _states(first))
    assert _states(second)[-1][0] == "TASK_STATE_COMPLETED"
    assert sum(text.startswith("Plan de investigación") for _, text in _states(second)) == 1
    assert any("Bilbao (municipio)" in text for _, text in _states(second))
    reply_prompt = model.calls[1][1].content
    assert '<turn n="1">¿Y los precios?</turn>' in reply_prompt
    assert '<turn n="2">Alquiler en Bilbao</turn>' in reply_prompt


async def test_clarification_limit_rejects():
    client, _ = _client([ambiguous(), ambiguous()], max_clarification_rounds=1)
    async with client:
        first = await _stream(client, _message("¿Y los precios?"))
        task_id, context_id = _ids(first)
        second = await _stream(client, _message("No sé", task_id, context_id))

    assert _states(first)[-1][0] == "TASK_STATE_INPUT_REQUIRED"
    state, text = _states(second)[-1]
    assert state == "TASK_STATE_REJECTED"
    assert text.startswith("No he podido interpretar la pregunta")


async def test_empty_identifiers_start_separate_tasks():
    client, model = _client([classification(), plan(), classification(), plan()])
    async with client:
        first = await _stream(client, _message("Alquileres en Madrid"))
        second = await _stream(client, _message("Alquileres en Sevilla"))

    first_ids, second_ids = _ids(first), _ids(second)
    assert all(first_ids) and all(second_ids)
    assert first_ids[0] != second_ids[0]
    assert first_ids[1] != second_ids[1]
    assert "Madrid" not in model.calls[2][1].content


@pytest.mark.parametrize(
    ("parts", "expected"),
    [
        ([{"text": "x" * 2001}], "2.000 caracteres"),
        ([{"text": "a"}, {"text": "b"}], "Solo se acepta una pregunta"),
        ([{"text": "   "}], "Escribe una pregunta"),
    ],
)
async def test_intake_limits_reject_without_a_model_call(parts, expected):
    client, model = _client([])
    async with client:
        events = await _stream(client, _message("", parts=parts))

    state, text = _states(events)[-1]
    assert state == "TASK_STATE_REJECTED"
    assert expected in text
    assert model.calls == []


async def test_model_error_fails_without_detail():
    client, _ = _client([ConnectionError("connection refused to 127.0.0.1:1234")])
    async with client:
        events = await _stream(client, _message("Alquileres en Madrid"))

    state, text = _states(events)[-1]
    assert state == "TASK_STATE_FAILED"
    assert text == FIXED_FAILURE


async def test_invalid_plan_on_every_attempt_fails():
    client, _ = _client([classification(), plan(media_step())], http_max_retries=0)
    async with client:
        events = await _stream(client, _message("Alquileres en Madrid"))

    states = _states(events)
    assert states[-1] == ("TASK_STATE_FAILED", FIXED_FAILURE)
    assert states[-2][1].startswith("Entendido")
    assert not any(text.startswith("Plan de investigación") for _, text in states)


class SlowModel(FakeStructuredChatModel):
    def with_structured_output(self, schema, **kwargs):
        from langchain_core.runnables import RunnableLambda

        async def respond(_messages):
            await asyncio.sleep(5)

        return RunnableLambda(respond)


async def test_request_timeout_fails():
    app = create_app(_settings(request_timeout_seconds=0.05), SlowModel(), FakeSearchTool())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000") as client:
        events = await _stream(client, _message("Alquileres en Madrid"))

    assert _states(events)[-1] == ("TASK_STATE_FAILED", FIXED_FAILURE)
