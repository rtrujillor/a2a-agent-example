import pytest

from housing_access_agent.a2a.messages import (
    ASSUMPTION_LABELS,
    TOPIC_LABELS,
    Text,
    catalog_language,
    interpretation,
    plan_summary,
    search_update,
    sources_summary,
    text,
)
from housing_access_agent.domain.enums import Assumption, GapReason, SourceKind, SourceType, ToolName, Topic
from housing_access_agent.domain.models import Evidence, ModelClassification, PlanStep, ResearchPlan, SearchGap
from housing_access_agent.workflow.classifier import apply_defaults
from tests.fakes import classification, source


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


def _step(sub_question, kind, sites=()):
    return PlanStep(
        sub_question=sub_question,
        tool=ToolName.WEB_SEARCH,
        query=f"consulta secreta {sub_question}",
        query_language="es",
        source_kind=kind,
        sites=list(sites),
    )


def test_spanish_plan_summary():
    plan = ResearchPlan(
        iteration=0,
        steps=[
            _step("¿Cuál es el alquiler medio en Bilbao?", SourceKind.OFFICIAL, ["ine.es"]),
            _step("¿Cómo ha evolucionado en Bizkaia?", SourceKind.OFFICIAL, ["mivau.gob.es"]),
            _step("¿Qué se ha publicado recientemente?", SourceKind.MEDIA),
            _step("¿Qué precios piden los portales?", SourceKind.MARKET),
        ],
    )

    summary = plan_summary(plan, "es")

    assert summary.splitlines() == [
        "Plan de investigación (4 búsquedas):",
        "- ¿Cuál es el alquiler medio en Bilbao? · fuentes oficiales",
        "- ¿Cómo ha evolucionado en Bizkaia? · fuentes oficiales",
        "- ¿Qué se ha publicado recientemente? · medios",
        "- ¿Qué precios piden los portales? · portales (precios de oferta)",
    ]
    assert "consulta secreta" not in summary
    assert "ine.es" not in summary and "mivau" not in summary


def test_english_plan_summary_with_one_step():
    plan = ResearchPlan(iteration=0, steps=[_step("What do portals ask?", SourceKind.MARKET)])

    assert plan_summary(plan, "en") == "Research plan (1 search):\n- What do portals ask? · portals (asking prices)"


def _search_plan():
    return ResearchPlan(
        iteration=0,
        steps=[
            _step("¿Qué se ha publicado?", SourceKind.MEDIA),
            _step("¿Cuál es el alquiler medio?", SourceKind.OFFICIAL, ["ine.es"]),
            _step("¿Qué piden los portales?", SourceKind.MARKET),
            _step("¿Qué dice el BOE?", SourceKind.OFFICIAL, ["boe.es"]),
        ],
    )


def _evidence(step, url):
    return Evidence(step=step, source=source(url))


def test_search_update_with_sources():
    evidence = [_evidence(0, "https://elpais.com/a")] + [_evidence(1, f"https://www.ine.es/{n}") for n in range(3)]

    update = search_update(_search_plan(), 1, evidence, [], "es")

    assert update.splitlines() == [
        "Búsqueda 2/4 · fuentes oficiales: ¿Cuál es el alquiler medio?",
        "Fuentes encontradas: 3.",
    ]
    for hidden in ("consulta secreta", "ine.es", "https://"):
        assert hidden not in update


@pytest.mark.parametrize(
    ("reason", "lang", "expected"),
    [
        (GapReason.EMPTY, "es", "Sin resultados."),
        (GapReason.FAILED, "es", "No se ha podido completar la búsqueda."),
        (GapReason.FAILED, "en", "The search could not be completed."),
    ],
)
def test_search_update_for_gaps(reason, lang, expected):
    update = search_update(_search_plan(), 2, [], [SearchGap(step=2, reason=reason)], lang)

    assert update.splitlines()[1] == expected
    assert update.splitlines()[0].endswith(("portales (precios de oferta): ¿Qué piden los portales?",
                                            "portals (asking prices): ¿Qué piden los portales?"))


def test_sources_summary_by_type():
    evidence = (
        [_evidence(0, f"https://www.ine.es/{n}") for n in range(4)]
        + [_evidence(1, f"https://elpais.com/{n}") for n in range(3)]
        + [_evidence(2, f"https://www.idealista.com/{n}") for n in range(2)]
        + [_evidence(3, "https://example-blog.com/x")]
    )

    summary = sources_summary(evidence, [SearchGap(step=3, reason=GapReason.EMPTY)], "es")

    assert summary.splitlines() == [
        "Fuentes encontradas: 10 (oficiales: 4 · medios: 3 · portales (precios de oferta): 2 · otras: 1).",
        "Búsquedas sin resultados: 1.",
        text(Text.NOT_VALIDATED, "es"),
    ]
    assert "validación" in summary and "https://" not in summary


def test_english_sources_summary_skips_empty_types():
    summary = sources_summary([_evidence(0, "https://www.boe.es/a")], [], "en")

    assert summary.splitlines()[:2] == ["Sources found: 1 (official: 1).", "Searches without results: 0."]
    assert summary.splitlines()[2].startswith("Source validation and the written answer are not available yet")


def test_every_source_type_has_a_label():
    from housing_access_agent.a2a.messages import SOURCE_TYPE_LABELS

    for lang in ("es", "en"):
        assert set(SOURCE_TYPE_LABELS[lang]) == set(SourceType)
