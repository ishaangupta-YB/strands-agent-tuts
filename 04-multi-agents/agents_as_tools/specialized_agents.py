"""
Specialized agent tools for the "Agents as Tools" multi-agent pattern.

Each function is a @tool-decorated wrapper around a focused Agent instance.
The orchestrator calls these exactly like any other Strands tool.

Key design decisions:
  - callback_handler=None on sub-agents → suppresses their internal output,
    so only the orchestrator's streaming response reaches the terminal.
  - Each agent has a tight system_prompt scoped to its domain.
  - _extract() pulls plain text from the AgentResult message.
"""
from pathlib import Path
from dotenv import load_dotenv
from strands import Agent, tool
from strands_tools import http_request, calculator, current_time
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# ── Shared model config ────────────────────────────────────────────────────────

_boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)


def _make_model() -> BedrockModel:
    return BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        boto_client_config=_boto_config,
    )


def _extract(result) -> str:
    """Pull plain text out of an AgentResult."""
    try:
        content = result.message.get("content", [])
        texts = [b["text"] for b in content if isinstance(b, dict) and "text" in b]
        return "\n".join(texts) if texts else str(result)
    except Exception:
        return str(result)


# ── Specialized tool agents ────────────────────────────────────────────────────

@tool
def research_assistant(query: str) -> str:
    """
    Answer research questions requiring factual, well-sourced information.
    Use for questions about history, science, current events, concepts,
    or any topic where verified facts and explanations are needed.

    Args:
        query: A research question requiring factual information.

    Returns:
        A detailed, accurate answer with sources where possible.
    """
    try:
        agent = Agent(
            model=_make_model(),
            system_prompt=(
                "You are a focused research assistant. Your job is to provide accurate, "
                "factual answers. Use http_request to fetch information from reliable sources "
                "when needed. Be concise yet thorough. Always cite URLs or sources when you "
                "retrieve information from the web."
            ),
            tools=[http_request],
            callback_handler=None,  # silence sub-agent output
        )
        return _extract(agent(query))
    except Exception as e:
        return f"Research assistant error: {e}"


@tool
def product_recommendation_assistant(query: str) -> str:
    """
    Provide product recommendations and shopping advice based on user preferences,
    budget, and intended use case. Use for buying decisions, gear selection,
    product comparisons, or finding the right item for a specific need.

    Args:
        query: A product inquiry including preferences, budget, or use case.

    Returns:
        Specific product recommendations with names, price ranges, and reasoning.
    """
    try:
        agent = Agent(
            model=_make_model(),
            system_prompt=(
                "You are a knowledgeable product recommendation specialist. "
                "Suggest specific products with brand names, model numbers, and price ranges. "
                "Explain clearly why each recommendation suits the user's needs. "
                "Use calculator to work out budget breakdowns or price comparisons when relevant. "
                "Use http_request to look up current products or reviews when needed."
            ),
            tools=[calculator, http_request],
            callback_handler=None,
        )
        return _extract(agent(query))
    except Exception as e:
        return f"Product recommendation error: {e}"


@tool
def trip_planning_assistant(query: str) -> str:
    """
    Create travel itineraries and provide destination-specific travel advice.
    Use for trip planning, destination recommendations, packing lists, travel
    logistics, or understanding what to expect at a specific location.

    Args:
        query: A travel planning request with destination, dates, or preferences.

    Returns:
        A practical itinerary or detailed travel advice tailored to the query.
    """
    try:
        agent = Agent(
            model=_make_model(),
            system_prompt=(
                "You are an experienced trip planning specialist with deep knowledge of "
                "destinations worldwide. Create practical, day-by-day itineraries when asked. "
                "Always factor in season, weather conditions, and local logistics. "
                "Use current_time to understand timing context (e.g. 'next month'). "
                "Use http_request to fetch up-to-date travel information, visa requirements, "
                "or weather conditions when relevant."
            ),
            tools=[http_request, current_time],
            callback_handler=None,
        )
        return _extract(agent(query))
    except Exception as e:
        return f"Trip planning error: {e}"
