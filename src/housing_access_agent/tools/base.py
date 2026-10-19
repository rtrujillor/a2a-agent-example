"""Shared interfaces and result types for retrieval tools."""

from datetime import date, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from housing_access_agent.domain.enums import Freshness, SourceType, ToolName


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


@runtime_checkable
class SearchTool(Protocol):
    """A retrieval tool a plan step can name."""

    @property
    def name(self) -> ToolName: ...

    async def run(self, query: SearchQuery) -> list[SourceResult]: ...
