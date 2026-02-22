"""
Agents as Tools — Multi-Agent Orchestrator
==========================================
An orchestrator agent that routes user queries to three specialized sub-agents:

  research_assistant               → factual / research questions
  product_recommendation_assistant → shopping, gear, buying advice
  trip_planning_assistant          → travel itineraries & destination advice

The orchestrator decides which specialist(s) to call. For compound queries
(e.g. "I need hiking boots for Patagonia") it chains multiple agents and
synthesises their answers into one cohesive response.

Usage:
  python main.py          # interactive chat
  python main.py --demo   # run preset example queries that show each routing path
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env before any strands imports
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from strands import Agent
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

from specialized_agents import (
    research_assistant,
    product_recommendation_assistant,
    trip_planning_assistant,
)

# ── Model ──────────────────────────────────────────────────────────────────────

_boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    boto_client_config=_boto_config,
)

# ── Orchestrator ───────────────────────────────────────────────────────────────

ORCHESTRATOR_PROMPT = """
You are a smart routing assistant with access to three specialized expert agents.
Choose the right specialist(s) based on the user's query:

  - research_assistant               → factual questions, science, history, concepts,
                                        current events, how things work
  - product_recommendation_assistant → what to buy, gear, gadgets, product comparisons,
                                        shopping advice, budget recommendations
  - trip_planning_assistant          → travel itineraries, destination advice,
                                        packing lists, what to expect in a location

For compound queries spanning multiple domains (e.g. "I need hiking boots for a Patagonia trip"),
call the relevant agents in sequence and synthesise their answers into one clear, cohesive response.

For simple conversational questions that don't require specialised knowledge, answer directly
without calling any tool.

Always be helpful, specific, and concise in your final response.
""".strip()

orchestrator = Agent(
    model=model,
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[
        research_assistant,
        product_recommendation_assistant,
        trip_planning_assistant,
    ],
)

# ── Demo queries ───────────────────────────────────────────────────────────────

DEMO_QUERIES = [
    # 1. Single-domain: research
    "What causes the Northern Lights and which locations offer the best viewing?",

    # 2. Single-domain: product recommendation
    "I need a noise-cancelling headphone under $300 for a daily commute.",

    # 3. Single-domain: trip planning
    "Plan a 5-day trip to Kyoto, Japan for someone who loves temples and street food.",

    # 4. Multi-domain: travel context + product recommendation (compound chain)
    (
        "I'm going hiking in Patagonia next month. "
        "What should I know about the region's terrain and weather, "
        "and what hiking boots would you recommend for those conditions?"
    ),
]

# ── Entry points ───────────────────────────────────────────────────────────────

def run_demo():
    print("=" * 65)
    print("  Agents as Tools — Demo Mode")
    print("=" * 65)
    print("Routing four queries through the orchestrator:\n")
    print("  [1] Research        → research_assistant")
    print("  [2] Product         → product_recommendation_assistant")
    print("  [3] Travel          → trip_planning_assistant")
    print("  [4] Compound        → trip_planning_assistant + product_recommendation_assistant")
    print("=" * 65)

    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n[Query {i}/{len(DEMO_QUERIES)}]")
        print(f"  {query}")
        print("-" * 65)
        orchestrator(query)
        print()


def run_interactive():
    print("=" * 65)
    print("  Agents as Tools — Interactive Chat")
    print("=" * 65)
    print("Specialists available:")
    print("  • Research          (facts, science, history, how things work)")
    print("  • Product recs      (gear, gadgets, buying advice)")
    print("  • Trip planning     (itineraries, destinations, travel tips)")
    print()
    print("The orchestrator auto-routes to the right specialist(s).")
    print("Type 'exit' or 'quit' to end.")
    print("=" * 65)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "q", "bye"}:
                print("\nGoodbye!")
                break

            print("\nOrchestrator: ", end="", flush=True)
            orchestrator(user_input)
            print("\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_interactive()
