"""Agent-card metadata and advertised capabilities."""

from importlib.metadata import PackageNotFoundError, version

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.utils.constants import PROTOCOL_VERSION_CURRENT, TransportProtocol

from housing_access_agent.config import Settings

TEXT_MODES = ["text/plain"]


def _package_version() -> str:
    try:
        return version("spain-housing-access-agent")
    except PackageNotFoundError:
        return "0.0.0"


def build_agent_card(settings: Settings) -> AgentCard:
    """Public description of the agent. Holds no secrets."""
    return AgentCard(
        name="Spain Housing Access Agent",
        description=(
            "Researches housing access in Spain with current, verifiable evidence: prices, rents, "
            "wages, supply, legislation, public policy, tourism, and social movements. "
            "Answers are neutral, cited, and state their limitations. No personal legal or "
            "financial advice, valuations, or forecasts."
        ),
        version=_package_version(),
        supported_interfaces=[
            AgentInterface(
                url=settings.a2a_agent_url,
                protocol_binding=TransportProtocol.JSONRPC.value,
                protocol_version=PROTOCOL_VERSION_CURRENT,
            )
        ],
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=TEXT_MODES,
        default_output_modes=TEXT_MODES,
        skills=[
            AgentSkill(
                id="housing-access-research",
                name="Housing access research",
                description=(
                    "Interprets a question about housing in Spain, its autonomous communities, "
                    "provinces, municipalities, or neighborhoods, and researches it."
                ),
                tags=["housing", "spain", "rents", "prices", "policy"],
                examples=[
                    "¿Qué factores afectan al acceso a la vivienda de alquiler en Madrid?",
                    "¿Cómo han evolucionado los alquileres en Barcelona desde 2020?",
                    "What public housing measures have recently been announced in Spain?",
                ],
                input_modes=TEXT_MODES,
                output_modes=TEXT_MODES,
            )
        ],
    )
