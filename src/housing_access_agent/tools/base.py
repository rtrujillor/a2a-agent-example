"""Shared interfaces, result types, and errors for retrieval tools."""

from enum import StrEnum
from typing import Protocol, runtime_checkable

from housing_access_agent.domain.enums import ToolName
from housing_access_agent.domain.models import SearchQuery, SourceResult

__all__ = ["SearchErrorCategory", "SearchQuery", "SearchTool", "SearchToolError", "SourceResult"]


class SearchErrorCategory(StrEnum):
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    RATE_LIMITED = "rate_limited"
    SERVER = "server"
    REJECTED = "rejected"
    INVALID_RESPONSE = "invalid_response"


class SearchToolError(Exception):
    """A search that failed; the category is safe to log, the provider's text is not kept."""

    def __init__(self, category: SearchErrorCategory):
        super().__init__(category.value)
        self.category = category


@runtime_checkable
class SearchTool(Protocol):
    """A retrieval tool a plan step can name."""

    @property
    def name(self) -> ToolName: ...

    async def run(self, query: SearchQuery) -> list[SourceResult]: ...
