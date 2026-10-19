"""Tools a plan may use, official-domain allowlists, and source typing by domain."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from housing_access_agent.domain.enums import SourceType, ToolName, Topic

# National official sources by topic. Regional authorities are not listed yet.
OFFICIAL_DOMAINS: Mapping[Topic, tuple[str, ...]] = {
    Topic.PRICES: ("ine.es", "mivau.gob.es", "bde.es", "registradores.org", "notariado.org"),
    Topic.RENTS: ("ine.es", "mivau.gob.es", "boe.es"),
    Topic.WAGES_AND_AFFORDABILITY: ("ine.es", "bde.es", "mivau.gob.es"),
    Topic.SUPPLY_AND_CONSTRUCTION: ("ine.es", "mivau.gob.es"),
    Topic.PUBLIC_AND_SOCIAL_HOUSING: ("mivau.gob.es", "boe.es"),
    Topic.TENANT_RIGHTS_AND_LEGISLATION: ("boe.es", "mivau.gob.es", "poderjudicial.es"),
    Topic.TOURISM_AND_SHORT_TERM_RENTALS: ("ine.es", "mivau.gob.es", "boe.es"),
    Topic.INVESTMENT: ("bde.es", "ine.es", "registradores.org"),
    Topic.VACANT_HOMES: ("ine.es", "mivau.gob.es"),
    Topic.DISPLACEMENT: ("ine.es", "poderjudicial.es"),
    Topic.PUBLIC_POLICY: ("boe.es", "mivau.gob.es", "lamoncloa.gob.es"),
}

# Listing portals and appraisal firms: asking prices and valuations, not transactions.
MARKET_DOMAINS: tuple[str, ...] = (
    "idealista.com",
    "fotocasa.es",
    "pisos.com",
    "habitaclia.com",
    "tinsa.es",
    "st-tasacion.es",
)

MEDIA_DOMAINS: tuple[str, ...] = (
    "elpais.com",
    "elmundo.es",
    "abc.es",
    "lavanguardia.com",
    "elperiodico.com",
    "eldiario.es",
    "elconfidencial.com",
    "20minutos.es",
    "rtve.es",
    "efe.com",
    "europapress.es",
    "expansion.com",
    "eleconomista.es",
    "elcorreo.com",
    "lavozdegalicia.es",
)


def normalize_domain(domain: str) -> str:
    """Lower-case a domain and strip a leading `www.`."""
    domain = domain.strip().lower().rstrip(".")
    return domain.removeprefix("www.")


def domain_matches(domain: str, allowed: Iterable[str]) -> bool:
    """True when the domain is an allowed domain or one of its subdomains."""
    domain = normalize_domain(domain)
    return any(domain == item or domain.endswith(f".{item}") for item in allowed)


@dataclass(frozen=True)
class ToolCatalog:
    """The tools and allowlists the planner enforces."""

    tools: frozenset[ToolName] = frozenset({ToolName.WEB_SEARCH})
    official_domains: Mapping[Topic, tuple[str, ...]] = field(default_factory=lambda: dict(OFFICIAL_DOMAINS))
    market_domains: tuple[str, ...] = MARKET_DOMAINS
    media_domains: tuple[str, ...] = MEDIA_DOMAINS

    def tool(self, name: str) -> ToolName | None:
        """The catalog tool with this name, or None."""
        try:
            tool = ToolName(name.strip())
        except ValueError:
            return None
        return tool if tool in self.tools else None

    def allowlist(self, topic: Topic | None) -> tuple[str, ...]:
        """Official domains for a topic; empty when it has none."""
        return self.official_domains.get(topic, ()) if topic is not None else ()

    def domain_allowed(self, domain: str, topic: Topic | None) -> bool:
        return domain_matches(domain, self.allowlist(topic))

    def source_type_for(self, url: str) -> SourceType:
        """Classify a result's source from its URL's domain."""
        try:
            parts = urlsplit(url.strip())
        except ValueError:
            return SourceType.OTHER
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return SourceType.OTHER
        host = parts.hostname
        official = {domain for domains in self.official_domains.values() for domain in domains}
        if domain_matches(host, official):
            return SourceType.OFFICIAL
        if domain_matches(host, self.market_domains):
            return SourceType.MARKET
        if domain_matches(host, self.media_domains):
            return SourceType.MEDIA
        return SourceType.OTHER


DEFAULT_CATALOG = ToolCatalog()
