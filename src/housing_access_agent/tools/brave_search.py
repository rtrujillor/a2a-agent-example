"""Brave Search API adapter for the `web_search` tool."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

import httpx

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import Freshness, ToolName
from housing_access_agent.domain.models import SearchQuery, SourceResult
from housing_access_agent.tools.base import SearchErrorCategory, SearchToolError
from housing_access_agent.tools.catalog import DEFAULT_CATALOG, ToolCatalog, normalize_domain

logger = logging.getLogger(__name__)

# A constant, not a setting: searches may only reach this host.
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
MAX_COUNT = 20
COUNTRY = "ES"
DEFAULT_LANGUAGE = "es"
# Brave `search_lang` codes for the languages requests arrive in; anything else uses Spanish.
SUPPORTED_LANGUAGES = frozenset({"es", "en", "ca", "eu", "gl"})
FRESHNESS = {Freshness.PAST_WEEK: "pw", Freshness.PAST_MONTH: "pm", Freshness.PAST_YEAR: "py"}

BACKOFF_SECONDS = 0.5
MAX_RETRY_AFTER_SECONDS = 10.0


RETRYABLE = frozenset(
    {
        SearchErrorCategory.TIMEOUT,
        SearchErrorCategory.CONNECTION,
        SearchErrorCategory.RATE_LIMITED,
        SearchErrorCategory.SERVER,
    }
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: object) -> str:
    """Text without markup or entities, with whitespace collapsed."""
    if not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return " ".join("".join(parser.parts).split())


def search_terms(query: SearchQuery) -> str:
    """The query, restricted to the step's sites with `site:` operators."""
    if not query.sites:
        return query.query
    if len(query.sites) == 1:
        return f"{query.query} site:{query.sites[0]}"
    return f"{query.query} ({' OR '.join(f'site:{site}' for site in query.sites)})"


def search_language(language: str) -> str:
    primary = language.strip().lower().replace("_", "-").split("-")[0]
    return primary if primary in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def request_params(query: SearchQuery) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "q": search_terms(query),
        "count": min(query.max_results, MAX_COUNT),
        "country": COUNTRY,
        "search_lang": search_language(query.language),
    }
    if query.freshness is not None:
        params["freshness"] = FRESHNESS[query.freshness]
    return params


def _published(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip()).date()
    except ValueError:
        return None


def _publisher(item: dict[str, Any], url: str) -> str:
    profile = item.get("profile")
    if isinstance(profile, dict) and (name := plain_text(profile.get("name"))):
        return name
    meta = item.get("meta_url")
    if isinstance(meta, dict) and (host := plain_text(meta.get("hostname"))):
        return normalize_domain(host)
    try:
        return normalize_domain(urlsplit(url).hostname or "")
    except ValueError:
        return ""


def parse_results(payload: object, catalog: ToolCatalog, retrieved_at: datetime) -> list[SourceResult]:
    """Map a Brave response to sources. The source type comes from the URL, never the content."""
    if not isinstance(payload, dict):
        raise SearchToolError(SearchErrorCategory.INVALID_RESPONSE)
    web = payload.get("web")
    items = web.get("results") if isinstance(web, dict) else None
    if not isinstance(items, list):
        return []
    results: list[SourceResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        url = url.strip()
        results.append(
            SourceResult(
                url=url,
                title=plain_text(item.get("title")),
                publisher=_publisher(item, url),
                published_at=_published(item.get("page_age")),
                retrieved_at=retrieved_at,
                source_type=catalog.source_type_for(url),
                snippet=plain_text(item.get("description")),
            )
        )
    return results


def _retry_after(response: httpx.Response) -> float:
    try:
        return min(max(float(response.headers.get("retry-after", "")), 0.0), MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        return 0.0


class BraveSearchTool:
    """`web_search` through the Brave Search API, with timeouts, retries, and pacing."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        settings: Settings,
        catalog: ToolCatalog = DEFAULT_CATALOG,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._client = client
        self._headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
        self._settings = settings
        self._catalog = catalog
        self._now = now
        self._monotonic = monotonic
        self._sleep = sleep
        self._last_request: float | None = None

    @property
    def name(self) -> ToolName:
        return ToolName.WEB_SEARCH

    async def _pace(self) -> None:
        """Keep consecutive requests at least the configured interval apart."""
        if self._last_request is not None:
            wait = self._settings.search_min_interval_seconds - (self._monotonic() - self._last_request)
            if wait > 0:
                await self._sleep(wait)
        self._last_request = self._monotonic()

    async def _attempt(self, params: dict[str, str | int]) -> tuple[object | None, SearchErrorCategory | None, float]:
        """One request: the payload, or the error category and how long the provider asks to wait."""
        await self._pace()
        try:
            response = await self._client.get(
                BRAVE_SEARCH_URL,
                params=params,
                headers=self._headers,
                timeout=self._settings.http_timeout_seconds,
            )
        except httpx.TimeoutException:
            return None, SearchErrorCategory.TIMEOUT, 0.0
        except httpx.TransportError:
            return None, SearchErrorCategory.CONNECTION, 0.0
        if response.status_code == 429:
            return None, SearchErrorCategory.RATE_LIMITED, _retry_after(response)
        if response.status_code >= 500:
            return None, SearchErrorCategory.SERVER, 0.0
        if response.status_code >= 400:
            return None, SearchErrorCategory.REJECTED, 0.0
        try:
            return response.json(), None, 0.0
        except ValueError:
            return None, SearchErrorCategory.INVALID_RESPONSE, 0.0

    async def run(self, query: SearchQuery) -> list[SourceResult]:
        params = request_params(query)
        logger.debug("Brave search: %s", params)
        attempts = 1 + self._settings.http_max_retries
        for attempt in range(attempts):
            payload, error, retry_after = await self._attempt(params)
            if error is None:
                return parse_results(payload, self._catalog, self._now())[: query.max_results]
            logger.debug("Brave search attempt %d failed: %s", attempt + 1, error.value)
            if error not in RETRYABLE or attempt + 1 == attempts:
                raise SearchToolError(error)
            await self._sleep(max(BACKOFF_SECONDS * 2**attempt, retry_after))
        raise SearchToolError(SearchErrorCategory.SERVER)  # pragma: no cover - the loop always returns or raises
