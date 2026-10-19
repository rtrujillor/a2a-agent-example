"""Research modes, source types, and verification-status values."""

from enum import StrEnum


class Verdict(StrEnum):
    """Scope verdict returned by the model for a request."""

    IN_SCOPE = "in_scope"
    AMBIGUOUS = "ambiguous"
    OUT_OF_SCOPE = "out_of_scope"


class Topic(StrEnum):
    """Housing topics the agent researches."""

    PRICES = "prices"
    RENTS = "rents"
    WAGES_AND_AFFORDABILITY = "wages_and_affordability"
    SUPPLY_AND_CONSTRUCTION = "supply_and_construction"
    PUBLIC_AND_SOCIAL_HOUSING = "public_and_social_housing"
    TENANT_RIGHTS_AND_LEGISLATION = "tenant_rights_and_legislation"
    TOURISM_AND_SHORT_TERM_RENTALS = "tourism_and_short_term_rentals"
    INVESTMENT = "investment"
    VACANT_HOMES = "vacant_homes"
    DISPLACEMENT = "displacement"
    PROTESTS_AND_SOCIAL_MOVEMENTS = "protests_and_social_movements"
    PUBLIC_POLICY = "public_policy"
    OTHER = "other"


class LocationLevel(StrEnum):
    """Administrative level of a location in Spain."""

    SPAIN = "spain"
    AUTONOMOUS_COMMUNITY = "autonomous_community"
    PROVINCE = "province"
    MUNICIPALITY = "municipality"
    NEIGHBORHOOD = "neighborhood"
    UNSPECIFIED = "unspecified"


class ResearchDepth(StrEnum):
    """How deep the research for a request should go."""

    CURRENT_AFFAIRS = "current_affairs"
    EVIDENCE_ANALYSIS = "evidence_analysis"
    DEEP_INVESTIGATION = "deep_investigation"


class Assumption(StrEnum):
    """Defaults the agent applied while interpreting a request."""

    DEFAULT_LOCATION_SPAIN = "default_location_spain"
    DEFAULT_PERIOD_LATEST = "default_period_latest"
    LOCATION_LEVEL_UNSPECIFIED = "location_level_unspecified"
    NO_PERSONAL_ADVICE = "no_personal_advice"


class Outcome(StrEnum):
    """Result of interpreting a request, mapped to an A2A task state."""

    IN_SCOPE = "in_scope"
    NEEDS_CLARIFICATION = "needs_clarification"
    OUT_OF_SCOPE = "out_of_scope"
    CLARIFICATION_EXHAUSTED = "clarification_exhausted"


class ToolName(StrEnum):
    """Tools a research plan step may name."""

    WEB_SEARCH = "web_search"


class SourceKind(StrEnum):
    """Kind of source a plan step expects to find."""

    OFFICIAL = "official"
    MEDIA = "media"
    MARKET = "market"


class SourceType(StrEnum):
    """Kind of source a retrieved result comes from, set from its domain."""

    OFFICIAL = "official"
    MEDIA = "media"
    MARKET = "market"
    OTHER = "other"


class Freshness(StrEnum):
    """How recent search results must be."""

    PAST_WEEK = "past_week"
    PAST_MONTH = "past_month"
    PAST_YEAR = "past_year"
