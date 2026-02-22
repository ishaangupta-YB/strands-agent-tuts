"""
Agents as Tools — AgentCore Production App
==========================================
Multi-agent orchestrator deployed to Amazon Bedrock AgentCore.

Architecture:
  User request
    └── Orchestrator (session-aware, holds conversation memory)
          ├── research_assistant       → factual/research questions (tavily + http_request)
          ├── product_recommendation   → shopping/gear advice       (calculator + http_request)
          └── trip_planning_assistant  → travel itineraries         (tavily + http_request + current_time)

Session management: Each AgentCore session gets its own orchestrator instance so
multi-turn conversation memory is maintained across invocations within a session.
Specialist sub-agents are stateless — created fresh per tool call.

Deploy:
  agentcore configure --entrypoint 04-multi-agents/agents_as_tools/agentcore_app.py
  agentcore deploy --env TAVILY_API_KEY=$TAVILY_API_KEY

Local dev:
  agentcore dev
  ./chat.sh --dev
"""
from pathlib import Path
from dotenv import load_dotenv
from strands import Agent, tool
from strands_tools import http_request, calculator, current_time, tavily
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from bedrock_agentcore.runtime import BedrockAgentCoreApp, BedrockAgentCoreContext

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# ── Shared model config ────────────────────────────────────────────────────────

_boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)

_model_config = dict(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    streaming=True,
    boto_client_config=_boto_config,
)


def _make_model() -> BedrockModel:
    return BedrockModel(**_model_config)


def _extract(result) -> str:
    """Pull plain text out of an AgentResult."""
    try:
        content = result.message.get("content", [])
        texts = [b["text"] for b in content if isinstance(b, dict) and "text" in b]
        return "\n".join(texts) if texts else str(result)
    except Exception:
        return str(result)


# ── Specialized tool agents ────────────────────────────────────────────────────
# callback_handler=None on sub-agents → their internal output is suppressed;
# only the orchestrator's response is returned to the caller.

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
                "You are a focused research assistant. Provide accurate, factual answers. "
                "Use tavily to search the web for current or detailed information. "
                "Use http_request for direct URL lookups. Always cite your sources."
            ),
            tools=[tavily, http_request],
            callback_handler=None,
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
                "Use calculator to work out budget breakdowns or comparisons. "
                "Use http_request to look up current product details or reviews."
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
                "You are an experienced trip planning specialist. Create practical, "
                "day-by-day itineraries when asked. Factor in season, weather, and logistics. "
                "Use tavily to fetch up-to-date travel info, visa requirements, and conditions. "
                "Use current_time to understand timing context (e.g. 'next month'). "
                "Use http_request for direct lookups when a URL is known."
            ),
            tools=[tavily, http_request, current_time],
            callback_handler=None,
        )
        return _extract(agent(query))
    except Exception as e:
        return f"Trip planning error: {e}"


# ── Orchestrator system prompt ─────────────────────────────────────────────────

ORCHESTRATOR_PROMPT = """
You are a smart routing assistant with access to three specialized expert agents.
Choose the right specialist(s) based on the user's query:

  - research_assistant               → factual questions, science, history, current events,
                                        how things work, anything needing verified facts
  - product_recommendation_assistant → what to buy, gear, gadgets, product comparisons,
                                        shopping advice, budget recommendations
  - trip_planning_assistant          → travel itineraries, destination advice, packing lists,
                                        what to expect in a location, travel logistics

For compound queries spanning multiple domains (e.g. "I need hiking boots for a Patagonia trip"),
call the relevant agents in sequence and synthesise their answers into one cohesive response.

For simple conversational questions that don't require specialised knowledge, answer directly.

This is a multi-turn conversation — remember what the user said earlier and refer back naturally.
""".strip()

SPECIALIST_TOOLS = [
    research_assistant,
    product_recommendation_assistant,
    trip_planning_assistant,
]

# ── Session management ─────────────────────────────────────────────────────────
# Each AgentCore session gets its own orchestrator so conversation memory is
# preserved across multiple invocations within the same session.

agents_by_session: dict[str, Agent] = {}


def get_or_create_orchestrator(session_id: str) -> Agent:
    """Return existing orchestrator for this session, or create a new one."""
    if session_id not in agents_by_session:
        agents_by_session[session_id] = Agent(
            model=_make_model(),
            system_prompt=ORCHESTRATOR_PROMPT,
            tools=SPECIALIST_TOOLS,
        )
    return agents_by_session[session_id]


# ── AgentCore app ──────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    """Route user input to the session's orchestrator."""
    session_id = BedrockAgentCoreContext.get_session_id() or "default"
    orchestrator = get_or_create_orchestrator(session_id)
    user_message = payload.get("prompt", "Hello")
    result = orchestrator(user_message)
    return str(result)


if __name__ == "__main__":
    app.run()
