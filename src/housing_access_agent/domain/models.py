"""Structured requests, evidence, citations, and response models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from housing_access_agent.domain.enums import (
    Assumption,
    LocationLevel,
    ResearchDepth,
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
