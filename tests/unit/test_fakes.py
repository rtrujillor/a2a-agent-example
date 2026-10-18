import pytest
from pydantic import ValidationError

from housing_access_agent.domain.models import ModelClassification
from tests.fakes import FakeStructuredChatModel, ambiguous, classification


async def test_scripted_results_come_back_in_order():
    model = FakeStructuredChatModel(script=[classification(), ambiguous(), RuntimeError("down")])
    runnable = model.with_structured_output(ModelClassification, method="json_schema")

    first = await runnable.ainvoke(["a"])
    second = await runnable.ainvoke(["b"])
    with pytest.raises(RuntimeError):
        await runnable.ainvoke(["c"])

    assert first.verdict == "in_scope"
    assert second.verdict == "ambiguous"
    assert len(model.calls) == 3
    assert model.methods == ["json_schema"]


async def test_invalid_payload_raises_validation_error():
    model = FakeStructuredChatModel(script=[classification(topic="football")])
    runnable = model.with_structured_output(ModelClassification)

    with pytest.raises(ValidationError):
        await runnable.ainvoke(["a"])
