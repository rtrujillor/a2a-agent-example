import pytest

from housing_access_agent.a2a.messages import (
    ASSUMPTION_LABELS,
    TOPIC_LABELS,
    Text,
    catalog_language,
    interpretation,
    text,
)
from housing_access_agent.domain.enums import Assumption, Topic
from housing_access_agent.domain.models import ModelClassification
from housing_access_agent.workflow.classifier import apply_defaults
from tests.fakes import classification


def _classified(**overrides):
    return apply_defaults(ModelClassification.model_validate(classification(**overrides)))


@pytest.mark.parametrize(
    ("language", "expected"),
    [("es", "es"), ("en", "en"), ("EN-gb", "en"), ("ca", "es"), ("eu", "es"), ("", "es"), (None, "es")],
)
def test_catalog_language(language, expected):
    assert catalog_language(language) == expected


def test_fixed_texts_exist_in_both_languages():
    for key in Text:
        assert text(key, "es")
        assert text(key, "en")
    assert text(Text.FAILURE, "ca") == text(Text.FAILURE, "es")


@pytest.mark.parametrize("lang", ["es", "en"])
def test_every_topic_and_assumption_has_a_label(lang):
    assert set(TOPIC_LABELS[lang]) == set(Topic)
    assert set(ASSUMPTION_LABELS[lang]) == set(Assumption)


def test_interpretation_of_a_specified_question():
    result = interpretation(_classified())

    assert result == "Entendido: alquileres · Madrid (municipio) · desde 2020."


def test_interpretation_with_defaults_in_spanish():
    result = interpretation(_classified(location=None, period=None))

    assert result.startswith("Entendido: alquileres · España · últimos datos disponibles.")
    assert "se considera España en su conjunto" in result
    assert "se usan los últimos datos disponibles" in result


def test_interpretation_in_english_with_reframe():
    result = interpretation(
        _classified(
            language="en",
            location={"name": "Valencia", "level": "unspecified"},
            period=None,
            reframed_question="Current state and recent trend of the Valencia housing market",
        )
    )

    assert result.startswith("Understood: rents · Valencia · latest available data.")
    assert "Question to research: Current state" in result
    assert "no personal advice is given" in result
    assert "the level with the best data will be used" in result


def test_interpretation_falls_back_to_spanish_labels():
    assert interpretation(_classified(language="ca")).startswith("Entendido:")
