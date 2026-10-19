"""Run one research plan step per pass and keep its sources with their provenance."""

import logging
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from housing_access_agent.config import Settings
from housing_access_agent.domain.enums import GapReason, ToolName
from housing_access_agent.domain.models import Evidence, PlanStep, SearchGap, SearchQuery, SourceResult
from housing_access_agent.state import ResearchState
from housing_access_agent.tools.base import SearchTool, SearchToolError
from housing_access_agent.tools.catalog import domain_matches

logger = logging.getLogger(__name__)

ResearcherNode = Callable[[ResearchState], Awaitable[dict[str, Any]]]


def research_done(state: ResearchState) -> bool:
    """True when every step of the current plan has been researched."""
    plan = state.get("plan")
    return plan is None or state.get("research_step", 0) >= len(plan.steps)


def url_key(url: str) -> str | None:
    """A URL's identity for deduplication, or None when it is not a web URL."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return None
    netloc = parts.hostname.lower() + (f":{parts.port}" if parts.port else "")
    return urlunsplit((parts.scheme.lower(), netloc, parts.path.rstrip("/"), parts.query, ""))


def _on_sites(url: str, sites: list[str]) -> bool:
    host = urlsplit(url.strip()).hostname or ""
    return domain_matches(host, sites)


def keep_results(
    step: PlanStep, results: Iterable[SourceResult], seen: set[str], limit: int
) -> list[SourceResult]:
    """Web URLs only, on the step's sites when it has any, new to this request, at most `limit`."""
    kept: list[SourceResult] = []
    for result in results:
        if len(kept) == limit:
            break
        key = url_key(result.url)
        if key is None or key in seen:
            continue
        if step.sites and not _on_sites(result.url, step.sites):
            continue
        seen.add(key)
        kept.append(result)
    return kept


def make_researcher(tools: Mapping[ToolName, SearchTool], settings: Settings) -> ResearcherNode:
    """Build the research node around injected search tools. It never calls the model."""

    async def research(state: ResearchState) -> dict[str, Any]:
        plan = state.get("plan")
        index = state.get("research_step", 0)
        if plan is None or index >= len(plan.steps):
            return {}
        step = plan.steps[index]
        evidence = list(state.get("evidence") or [])
        gaps = list(state.get("gaps") or [])
        searches_used = state.get("searches_used", 0)
        update: dict[str, Any] = {"research_step": index + 1}

        tool = tools.get(step.tool)
        if tool is None or searches_used >= settings.max_searches_per_request:
            # The planner prevents both; a step that can't run is a gap, never an extra search.
            logger.warning("Step %d not searched: %s", index + 1, "no tool" if tool is None else "budget used")
            gaps.append(SearchGap(step=index, reason=GapReason.FAILED))
            return update | {"gaps": gaps}

        query = SearchQuery(
            query=step.query,
            language=step.query_language,
            freshness=step.freshness,
            sites=step.sites,
            max_results=settings.max_results_per_search,
        )
        update["searches_used"] = searches_used + 1
        try:
            results = await tool.run(query)
        except SearchToolError as error:
            logger.warning("Step %d search failed: %s", index + 1, error.category.value)
            gaps.append(SearchGap(step=index, reason=GapReason.FAILED))
            return update | {"gaps": gaps}
        except Exception as error:
            logger.warning("Step %d search failed: %s", index + 1, type(error).__name__)
            gaps.append(SearchGap(step=index, reason=GapReason.FAILED))
            return update | {"gaps": gaps}

        seen = {key for item in evidence if (key := url_key(item.source.url))}
        kept = keep_results(step, results, seen, settings.max_results_per_search)
        logger.info("Step %d kept %d of %d results", index + 1, len(kept), len(results))
        if not kept:
            gaps.append(SearchGap(step=index, reason=GapReason.EMPTY))
            return update | {"gaps": gaps}
        evidence += [Evidence(step=index, source=source) for source in kept]
        return update | {"evidence": evidence}

    return research
