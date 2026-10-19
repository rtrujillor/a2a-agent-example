"""Structured requests, evidence, citations, and response models."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from housing_access_agent.domain.enums import (
    Assumption,
    Freshness,
    GapReason,
    LocationLevel,
    ResearchDepth,
    SourceKind,
    SourceType,
    ToolName,
    Topic,
    Verdict,
)


class Location(BaseModel):
    """A place in Spain and its administrative level."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Place name as the user wrote it.")
    level: LocationLevel


class Period(BaseModel):
    """The time span a request is about."""

    model_config = ConfigDict(extra="forbid")

    start_year: int | None = Field(default=None, description="First year, if stated.")
    end_year: int | None = Field(default=None, description="Last year, if stated.")
    label: str = Field(min_length=1, description="The period in the user's language.")


class ModelClassification(BaseModel):
    """What the language model extracts from a request. No defaults applied."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(
        min_length=2, description="Primary language tag of the user's messages, e.g. es, en, ca."
    )
    verdict: Verdict
    reason: str = Field(min_length=1, description="Why this verdict, in the user's language.")
    topic: Topic | None = Field(description="Main housing topic, or null if unclear.")
    location: Location | None = Field(description="Null when the user names no place.")
    period: Period | None = Field(description="Null when the user names no period.")
    intent: str = Field(description="What the user wants to know, in the user's language.")
    depth: ResearchDepth
    clarifying_question: str | None = Field(
        description="One question, in the user's language, only when the verdict is ambiguous."
    )
    reframed_question: str | None = Field(
        description="The researchable question without personal advice, when one applies."
    )

    @model_validator(mode="after")
    def _ambiguous_needs_question(self) -> "ModelClassification":
        if self.verdict is Verdict.AMBIGUOUS and not (self.clarifying_question or "").strip():
            raise ValueError("an ambiguous verdict needs a clarifying_question")
        return self


class ClassifiedRequest(BaseModel):
    """A request after the agent applied its defaults and assumptions."""

    language: str
    verdict: Verdict
    reason: str
    topic: Topic | None
    location: Location
    period: Period
    intent: str
    depth: ResearchDepth
    clarifying_question: str | None = None
    reframed_question: str | None = None
    assumptions: list[Assumption] = Field(default_factory=list)


class ModelPlanStep(BaseModel):
    """One step the language model proposes. The planner checks it in code."""

    model_config = ConfigDict(extra="forbid")

    sub_question: str = Field(description="What this step answers, in the user's language.")
    # A plain string: an unknown tool drops this step instead of failing the whole plan.
    tool: str = Field(description="Tool name from the allowed tools.")
    query: str = Field(description="Search query, without the user's personal circumstances.")
    query_language: str = Field(min_length=2, description="Language tag of the query, e.g. es.")
    source_kind: SourceKind
    freshness: Freshness | None = Field(description="How recent results must be, or null.")
    sites: list[str] = Field(description="Domains to restrict the search to, from the allowed domains only.")


class ModelPlan(BaseModel):
    """The research plan the language model proposes."""

    model_config = ConfigDict(extra="forbid")

    steps: list[ModelPlanStep]


class PlanStep(BaseModel):
    """A plan step after the planner enforced the catalog and allowlists."""

    sub_question: str
    tool: ToolName
    query: str = Field(min_length=1)
    query_language: str
    source_kind: SourceKind
    freshness: Freshness | None = None
    sites: list[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    """A bounded research plan for one planner iteration."""

    steps: list[PlanStep] = Field(min_length=1)
    iteration: int = Field(ge=0)


class SearchQuery(BaseModel):
    """One search a tool runs for a plan step."""

    query: str = Field(min_length=1)
    language: str
    freshness: Freshness | None = None
    sites: list[str] = Field(default_factory=list)
    max_results: int = Field(ge=1)


class SourceResult(BaseModel):
    """One retrieved source, with the metadata every citation needs."""

    url: str = Field(min_length=1)
    title: str
    publisher: str
    published_at: date | None = None
    retrieved_at: datetime
    # Set by the agent from the URL's domain, never by the source's content.
    source_type: SourceType
    snippet: str = ""


class Evidence(BaseModel):
    """A kept source and the plan step that found it."""

    step: int = Field(ge=0)
    source: SourceResult


class SearchGap(BaseModel):
    """A plan step that kept no source."""

    step: int = Field(ge=0)
    reason: GapReason
