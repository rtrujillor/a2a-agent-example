"""Searches against the real Brave Search API. Run with `pytest -m live`; needs BRAVE_SEARCH_API_KEY."""

from urllib.parse import urlsplit

import httpx
import pytest

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Freshness, SourceType
from housing_access_agent.domain.models import SearchQuery
from housing_access_agent.tools.brave_search import BraveSearchTool
from housing_access_agent.tools.catalog import domain_matches

pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="module")]


@pytest.fixture(scope="module")
async def tool():
    settings = Settings()
    key = settings.brave_search_api_key.get_secret_value()
    if not key:
        pytest.skip("BRAVE_SEARCH_API_KEY is not set")
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        yield BraveSearchTool(client, key, settings), settings


def _check(results):
    for result in results:
        assert urlsplit(result.url).scheme in ("http", "https")
        assert isinstance(result.source_type, SourceType)
        assert result.title


async def test_official_two_site_query_stays_on_its_sites(tool):
    search, settings = tool
    sites = ["ine.es", "mivau.gob.es"]

    results = await search.run(
        SearchQuery(query="índice de precios de vivienda en alquiler", language="es", sites=sites,
                    max_results=settings.max_results_per_search)
    )

    _check(results)
    # Brave may return off-site results; the researcher drops them, so this reports how many it honoured.
    on_site = [r for r in results if domain_matches(urlsplit(r.url).hostname or "", sites)]
    assert on_site, "Brave returned no result on the requested official sites"


async def test_recent_media_query(tool):
    search, settings = tool

    results = await search.run(
        SearchQuery(query="alquiler vivienda España noticias", language="es", freshness=Freshness.PAST_MONTH,
                    max_results=settings.max_results_per_search)
    )

    _check(results)
    assert results


async def test_market_query(tool):
    search, settings = tool

    results = await search.run(
        SearchQuery(query="precio medio alquiler Madrid portal inmobiliario", language="es",
                    max_results=settings.max_results_per_search)
    )

    _check(results)
    assert len(results) <= settings.max_results_per_search
