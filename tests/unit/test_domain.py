import pytest
from pydantic import ValidationError

from housing_access_agent.domain.enums import LocationLevel, SourceKind, Topic, Verdict
from housing_access_agent.domain.models import ModelClassification, ModelPlan, ModelPlanStep


def _payload(**overrides):
    payload = {
        "language": "es",
        "verdict": "in_scope",
        "reason": "Pregunta sobre alquileres en Madrid.",
        "topic": "rents",
        "location": {"name": "Madrid", "level": "municipality"},
        "period": {"start_year": 2020, "end_year": None, "label": "desde 2020"},
        "intent": "evolución de los alquileres",
        "depth": "evidence_analysis",
        "clarifying_question": None,
        "reframed_question": None,
    }
    payload.update(overrides)
    return payload


def test_parses_valid_classification():
    result = ModelClassification.model_validate(_payload())

    assert result.verdict is Verdict.IN_SCOPE
    assert result.topic is Topic.RENTS
    assert result.location.level is LocationLevel.MUNICIPALITY
    assert result.period.start_year == 2020


def test_location_and_period_may_be_null():
    result = ModelClassification.model_validate(_payload(location=None, period=None))

    assert result.location is None
    assert result.period is None


def test_ambiguous_without_question_is_invalid():
    with pytest.raises(ValidationError, match="clarifying_question"):
        ModelClassification.model_validate(_payload(verdict="ambiguous", clarifying_question=" "))


def test_ambiguous_with_question_is_valid():
    result = ModelClassification.model_validate(
        _payload(verdict="ambiguous", clarifying_question="¿Qué precios te interesan?")
    )

    assert result.clarifying_question


def test_unknown_topic_is_invalid():
    with pytest.raises(ValidationError):
        ModelClassification.model_validate(_payload(topic="football"))


def test_extra_fields_are_invalid():
    with pytest.raises(ValidationError):
        ModelClassification.model_validate(_payload(max_clarification_rounds=10))


def test_topic_set_matches_spec():
    assert len(Topic) == 13


def test_domain_has_no_io_imports():
    import housing_access_agent.domain.models as models

    source = open(models.__file__, encoding="utf-8").read()
    for module in ("httpx", "openai", "langchain", "langgraph", "a2a"):
        assert f"import {module}" not in source and f"from {module}" not in source


def _step(**overrides):
    step = {
        "sub_question": "¿Cuál es el alquiler medio en Madrid?",
        "tool": "web_search",
        "query": "índice de precios de alquiler Madrid",
        "query_language": "es",
        "source_kind": "official",
        "freshness": None,
        "sites": ["ine.es"],
    }
    step.update(overrides)
    return step


def test_parses_valid_plan():
    plan = ModelPlan.model_validate({"steps": [_step()]})

    assert plan.steps[0].source_kind is SourceKind.OFFICIAL


def test_plan_step_accepts_unknown_tool():
    step = ModelPlanStep.model_validate(_step(tool="ine_api"))

    assert step.tool == "ine_api"


def test_plan_step_extra_fields_are_invalid():
    with pytest.raises(ValidationError):
        ModelPlanStep.model_validate(_step(max_searches=20))


def test_plan_step_invalid_freshness_is_invalid():
    with pytest.raises(ValidationError):
        ModelPlanStep.model_validate(_step(freshness="yesterday"))
