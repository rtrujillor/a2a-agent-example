"""Plans built by the configured model. Run with `pytest -m live`."""

import httpx
import pytest

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Outcome, SourceKind
from housing_access_agent.server import build_chat_model
from housing_access_agent.tools.catalog import DEFAULT_CATALOG
from housing_access_agent.workflow.classifier import make_classifier
from housing_access_agent.workflow.planner import make_planner, plan_budget

# One event loop for the module: langchain-openai caches its async HTTP client,
# which is bound to the loop that first used it.
pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="module")]


@pytest.fixture(scope="module")
def nodes():
    settings = Settings()
    try:
        httpx.get(f"{settings.model_base_url.rstrip('/')}/models", timeout=3).raise_for_status()
    except httpx.HTTPError as error:
        pytest.skip(f"Model endpoint not reachable: {type(error).__name__}")
    model = build_chat_model(settings)
    return make_classifier(model, settings), make_planner(model, settings), settings


async def _plan(nodes, question):
    classify, plan, settings = nodes
    classified = await classify({"user_turns": [question], "clarification_rounds": 0})
    assert classified["outcome"] is Outcome.IN_SCOPE
    update = await plan({"user_turns": [question], **classified, "planner_iterations": 0, "searches_used": 0})
    return update["plan"], classified["classification"], settings


async def test_rents_plan_is_bounded_and_official_first(nodes):
    plan, classified, settings = await _plan(nodes, "¿Cómo han evolucionado los alquileres en Bilbao?")

    assert 1 <= len(plan.steps) <= plan_budget(settings, 0, 0)
    assert any(step.source_kind is SourceKind.OFFICIAL for step in plan.steps)
    allowlist = DEFAULT_CATALOG.allowlist(classified.topic)
    assert all(DEFAULT_CATALOG.domain_allowed(site, classified.topic) for step in plan.steps for site in step.sites)
    assert allowlist


async def test_personal_details_stay_out_of_queries(nodes):
    plan, _, _ = await _plan(nodes, "Gano 1.400 € al mes y tengo dos hijos, ¿puedo alquilar en Getafe?")

    for step in plan.steps:
        assert "1.400" not in step.query and "1400" not in step.query
        assert "hijos" not in step.query.lower()
