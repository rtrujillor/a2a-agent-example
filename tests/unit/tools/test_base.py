from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from housing_access_agent.domain.enums import SourceType, ToolName
from housing_access_agent.tools.base import SearchQuery, SearchTool, SourceResult


class FakeSearchTool:
    @property
    def name(self) -> ToolName:
        return ToolName.WEB_SEARCH

    async def run(self, query: SearchQuery) -> list[SourceResult]:
        return [
            SourceResult(
                url="https://www.ine.es/prensa/ipva.htm",
                title="Índice de precios de vivienda en alquiler",
                publisher="INE",
                retrieved_at=datetime(2026, 10, 19, tzinfo=UTC),
                source_type=SourceType.OFFICIAL,
            )
        ]


async def test_fake_tool_satisfies_protocol():
    tool = FakeSearchTool()

    results = await tool.run(SearchQuery(query="alquiler Bilbao", language="es", max_results=5))

    assert isinstance(tool, SearchTool)
    assert results[0].published_at is None


def test_result_needs_url():
    with pytest.raises(ValidationError):
        SourceResult(
            title="t", publisher="p", retrieved_at=datetime(2026, 10, 19, tzinfo=UTC), source_type="official"
        )


def test_result_needs_retrieval_date():
    with pytest.raises(ValidationError):
        SourceResult(url="https://ine.es", title="t", publisher="p", source_type="official")


def test_tools_do_not_import_model_or_graph():
    import housing_access_agent.tools.base as base

    source = open(base.__file__, encoding="utf-8").read()
    for module in ("langchain", "langgraph", "openai"):
        assert f"import {module}" not in source and f"from {module}" not in source
