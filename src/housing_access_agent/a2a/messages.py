"""Fixed user-facing texts in Spanish and English, and the interpretation summary."""

from enum import StrEnum

from housing_access_agent.domain.enums import Assumption, LocationLevel, Topic
from housing_access_agent.domain.models import ClassifiedRequest


class Text(StrEnum):
    INTAKE_EMPTY = "intake_empty"
    INTAKE_TOO_LONG = "intake_too_long"
    INTAKE_UNSUPPORTED = "intake_unsupported"
    NOT_AVAILABLE = "not_available"
    SCOPE_HINT = "scope_hint"
    REPHRASE = "rephrase"
    FAILURE = "failure"
    UNDERSTOOD = "understood"
    REFRAMED = "reframed"
    ASSUMPTIONS = "assumptions"
    LATEST_DATA = "latest_data"
    SPAIN = "spain"


_TEXTS: dict[str, dict[Text, str]] = {
    "es": {
        Text.INTAKE_EMPTY: "Escribe una pregunta sobre la vivienda en España.",
        Text.INTAKE_TOO_LONG: (
            "La pregunta supera el límite de 2.000 caracteres. Acórtala e inténtalo de nuevo."
        ),
        Text.INTAKE_UNSUPPORTED: "Solo se acepta una pregunta en texto, en un único mensaje.",
        Text.NOT_AVAILABLE: (
            "La investigación aún no está disponible: por ahora el agente solo interpreta la pregunta."
        ),
        Text.SCOPE_HINT: (
            "Este agente investiga el acceso a la vivienda en España: precios, alquileres, salarios, "
            "oferta, vivienda pública, derechos de inquilinos, turismo, inversión, viviendas vacías, "
            "desplazamiento, legislación y movilizaciones."
        ),
        Text.REPHRASE: (
            "No he podido interpretar la pregunta. Empieza de nuevo indicando qué quieres saber "
            "sobre la vivienda en España."
        ),
        Text.FAILURE: "No se ha podido procesar la solicitud. Inténtalo de nuevo más tarde.",
        Text.UNDERSTOOD: "Entendido",
        Text.REFRAMED: "Pregunta que se investigará",
        Text.ASSUMPTIONS: "Supuestos",
        Text.LATEST_DATA: "últimos datos disponibles",
        Text.SPAIN: "España",
    },
    "en": {
        Text.INTAKE_EMPTY: "Write a question about housing in Spain.",
        Text.INTAKE_TOO_LONG: "The question is longer than 2,000 characters. Shorten it and try again.",
        Text.INTAKE_UNSUPPORTED: "Only one text question is accepted, in a single message.",
        Text.NOT_AVAILABLE: "Research is not available yet: for now the agent only interprets the question.",
        Text.SCOPE_HINT: (
            "This agent researches housing access in Spain: prices, rents, wages, supply, public "
            "housing, tenant rights, tourism, investment, vacant homes, displacement, legislation, "
            "and social movements."
        ),
        Text.REPHRASE: (
            "I couldn't interpret the question. Start again and say what you want to know about "
            "housing in Spain."
        ),
        Text.FAILURE: "The request could not be processed. Please try again later.",
        Text.UNDERSTOOD: "Understood",
        Text.REFRAMED: "Question to research",
        Text.ASSUMPTIONS: "Assumptions",
        Text.LATEST_DATA: "latest available data",
        Text.SPAIN: "Spain",
    },
}

TOPIC_LABELS: dict[str, dict[Topic, str]] = {
    "es": {
        Topic.PRICES: "precios de la vivienda",
        Topic.RENTS: "alquileres",
        Topic.WAGES_AND_AFFORDABILITY: "salarios y asequibilidad",
        Topic.SUPPLY_AND_CONSTRUCTION: "oferta y construcción",
        Topic.PUBLIC_AND_SOCIAL_HOUSING: "vivienda pública y social",
        Topic.TENANT_RIGHTS_AND_LEGISLATION: "derechos de inquilinos y legislación",
        Topic.TOURISM_AND_SHORT_TERM_RENTALS: "turismo y alquiler de corta estancia",
        Topic.INVESTMENT: "inversión",
        Topic.VACANT_HOMES: "viviendas vacías",
        Topic.DISPLACEMENT: "desplazamiento",
        Topic.PROTESTS_AND_SOCIAL_MOVEMENTS: "protestas y movimientos sociales",
        Topic.PUBLIC_POLICY: "políticas públicas",
        Topic.OTHER: "otro tema de vivienda",
    },
    "en": {
        Topic.PRICES: "housing prices",
        Topic.RENTS: "rents",
        Topic.WAGES_AND_AFFORDABILITY: "wages and affordability",
        Topic.SUPPLY_AND_CONSTRUCTION: "supply and construction",
        Topic.PUBLIC_AND_SOCIAL_HOUSING: "public and social housing",
        Topic.TENANT_RIGHTS_AND_LEGISLATION: "tenant rights and legislation",
        Topic.TOURISM_AND_SHORT_TERM_RENTALS: "tourism and short-term rentals",
        Topic.INVESTMENT: "investment",
        Topic.VACANT_HOMES: "vacant homes",
        Topic.DISPLACEMENT: "displacement",
        Topic.PROTESTS_AND_SOCIAL_MOVEMENTS: "protests and social movements",
        Topic.PUBLIC_POLICY: "public policy",
        Topic.OTHER: "another housing topic",
    },
}

ASSUMPTION_LABELS: dict[str, dict[Assumption, str]] = {
    "es": {
        Assumption.DEFAULT_LOCATION_SPAIN: "no se indicó un lugar; se considera España en su conjunto",
        Assumption.DEFAULT_PERIOD_LATEST: "no se indicó un periodo; se usan los últimos datos disponibles",
        Assumption.LOCATION_LEVEL_UNSPECIFIED: (
            "no se indicó si es municipio, provincia o comunidad; se usará el nivel con mejores datos"
        ),
        Assumption.NO_PERSONAL_ADVICE: "no se ofrece asesoramiento personal; se analiza el mercado",
    },
    "en": {
        Assumption.DEFAULT_LOCATION_SPAIN: "no place was given; Spain as a whole is assumed",
        Assumption.DEFAULT_PERIOD_LATEST: "no period was given; the latest available data is used",
        Assumption.LOCATION_LEVEL_UNSPECIFIED: (
            "it was not said whether this is a municipality, province, or region; "
            "the level with the best data will be used"
        ),
        Assumption.NO_PERSONAL_ADVICE: "no personal advice is given; the market is analyzed instead",
    },
}

LEVEL_LABELS: dict[str, dict[LocationLevel, str]] = {
    "es": {
        LocationLevel.AUTONOMOUS_COMMUNITY: "comunidad autónoma",
        LocationLevel.PROVINCE: "provincia",
        LocationLevel.MUNICIPALITY: "municipio",
        LocationLevel.NEIGHBORHOOD: "barrio",
    },
    "en": {
        LocationLevel.AUTONOMOUS_COMMUNITY: "autonomous community",
        LocationLevel.PROVINCE: "province",
        LocationLevel.MUNICIPALITY: "municipality",
        LocationLevel.NEIGHBORHOOD: "neighborhood",
    },
}


def catalog_language(language: str | None) -> str:
    """English for English requests, Spanish for everything else."""
    primary = (language or "").strip().lower().replace("_", "-").split("-")[0]
    return "en" if primary == "en" else "es"


def text(key: Text, language: str | None = None) -> str:
    return _TEXTS[catalog_language(language)][key]


def interpretation(classified: ClassifiedRequest) -> str:
    """The agent's reading of an in-scope request, with every assumption."""
    lang = catalog_language(classified.language)
    parts: list[str] = []
    if classified.topic is not None:
        parts.append(TOPIC_LABELS[lang][classified.topic])

    if Assumption.DEFAULT_LOCATION_SPAIN in classified.assumptions:
        parts.append(_TEXTS[lang][Text.SPAIN])
    else:
        level = LEVEL_LABELS[lang].get(classified.location.level)
        parts.append(f"{classified.location.name} ({level})" if level else classified.location.name)

    if Assumption.DEFAULT_PERIOD_LATEST in classified.assumptions:
        parts.append(_TEXTS[lang][Text.LATEST_DATA])
    else:
        parts.append(classified.period.label)

    lines = [f"{_TEXTS[lang][Text.UNDERSTOOD]}: {' · '.join(parts)}."]
    if classified.reframed_question:
        lines.append(f"{_TEXTS[lang][Text.REFRAMED]}: {classified.reframed_question}")
    if classified.assumptions:
        labels = "; ".join(ASSUMPTION_LABELS[lang][a] for a in classified.assumptions)
        lines.append(f"{_TEXTS[lang][Text.ASSUMPTIONS]}: {labels}.")
    return "\n".join(lines)
