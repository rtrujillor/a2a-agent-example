import pytest

from housing_access_agent.domain.enums import SourceType, ToolName, Topic
from housing_access_agent.tools.catalog import DEFAULT_CATALOG, OFFICIAL_DOMAINS, domain_matches


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.ine.es/prensa/ipva.htm", SourceType.OFFICIAL),
        ("https://ine.es", SourceType.OFFICIAL),
        ("https://fakeine.es/x", SourceType.OTHER),
        ("https://www.idealista.com/informes", SourceType.MARKET),
        ("https://elpais.com/economia/", SourceType.MEDIA),
        ("https://cincodias.elpais.com/x", SourceType.MEDIA),
        ("https://unknown-blog.example/x", SourceType.OTHER),
        ("ftp://ine.es/file", SourceType.OTHER),
        ("javascript:alert(1)", SourceType.OTHER),
        ("not a url", SourceType.OTHER),
        ("http://[::1", SourceType.OTHER),
    ],
)
def test_source_type_from_domain(url, expected):
    assert DEFAULT_CATALOG.source_type_for(url) is expected


def test_subdomain_matching():
    assert domain_matches("WWW.INE.ES", ["ine.es"])
    assert domain_matches("estadisticas.ine.es", ["ine.es"])
    assert not domain_matches("fakeine.es", ["ine.es"])
    assert not domain_matches("ine.es.evil.com", ["ine.es"])


def test_topics_without_allowlist():
    assert DEFAULT_CATALOG.allowlist(Topic.PROTESTS_AND_SOCIAL_MOVEMENTS) == ()
    assert DEFAULT_CATALOG.allowlist(Topic.OTHER) == ()
    assert DEFAULT_CATALOG.allowlist(None) == ()


def test_allowlisted_domains_are_bare_lower_case():
    for domains in OFFICIAL_DOMAINS.values():
        for domain in domains:
            assert domain == domain.lower()
            assert "://" not in domain and "/" not in domain
            assert not domain.startswith("www.")


def test_catalog_tools():
    assert DEFAULT_CATALOG.tool("web_search") is ToolName.WEB_SEARCH
    assert DEFAULT_CATALOG.tool("ine_api") is None


def test_domain_allowed_by_topic():
    assert DEFAULT_CATALOG.domain_allowed("ine.es", Topic.RENTS)
    assert not DEFAULT_CATALOG.domain_allowed("poderjudicial.es", Topic.RENTS)
    assert not DEFAULT_CATALOG.domain_allowed("ine.es", Topic.OTHER)
