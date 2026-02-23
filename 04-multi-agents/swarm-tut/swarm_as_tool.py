"""
swarm_as_tool.py — "Swarm as a Tool" pattern
=============================================
In our main swarm.py, WE manually defined the 4 agents and built the Swarm
ourselves. That gives full control but requires knowing the agent team upfront.

This file shows a different approach: give a single outer Agent the `swarm`
tool from strands_tools. The outer agent then DECIDES ON ITS OWN:
  - what specialized sub-agents to create
  - what roles/system prompts to give them
  - what task to hand the swarm
  - how to interpret and summarize the swarm's output

Architecture:

  User query
      │
      ▼
  ┌─────────────────────────────┐
  │   Outer Agent (orchestrator) │  ← has one tool: `swarm`
  │   "Create a swarm to solve  │
  │    the user's query"        │
  └──────────────┬──────────────┘
                 │ calls swarm(...)
                 ▼
  ┌─────────────────────────────┐
  │  Dynamically created Swarm  │  ← agents defined by the outer LLM at runtime
  │  (e.g. researcher, analyst, │
  │   writer — LLM decides)     │
  └─────────────────────────────┘
                 │ SwarmResult
                 ▼
  ┌─────────────────────────────┐
  │   Outer Agent synthesizes   │  ← reads swarm output, writes final answer
  │   the results               │
  └─────────────────────────────┘

Key difference from swarm.py:
  swarm.py         → YOU define agents, YOU build Swarm, YOU run it
  swarm_as_tool.py → outer LLM defines agents, outer LLM runs swarm tool,
                     outer LLM synthesizes the result

Run:
  python 04-multi-agents/swarm-tut/swarm_as_tool.py
"""

import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

from botocore.config import Config as BotocoreConfig
from strands import Agent
from strands.models import BedrockModel
from strands_tools.swarm import swarm   

_boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)

_model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1",
    streaming=True,
    boto_client_config=_boto_config,
)


# ── Outer agent ───────────────────────────────────────────────────────────────────
# This agent has ONE tool: `swarm`. When the user gives it a complex query,
# it uses that tool to dynamically spin up a team of specialized agents,
# run them, and then interpret the results to produce a final answer.
#
# The outer agent's system prompt tells it HOW to use the swarm tool effectively —
# what kinds of agents to create, how to structure tasks, and how to synthesize output.

OUTER_SYSTEM_PROMPT = """You are an intelligent orchestrator that uses a swarm of
specialized agents to solve complex, multi-part queries.

WHEN YOU RECEIVE A QUERY:
1. Break the query into distinct work areas (e.g. research, analysis, writing)
2. Call the `swarm` tool with:
   - A list of specialized agent definitions (name + system_prompt for each)
   - A clear task description for the swarm
   - An appropriate entry_point (the agent who should receive the task first)
3. After the swarm completes, READ the returned results carefully
4. Synthesize the swarm output into a clear, well-structured final answer for the user

AGENT DESIGN TIPS:
- Create 2-4 agents with distinct, non-overlapping roles
- Give each agent a clear system_prompt that says when to hand off (to which agent)
- Use lowercase agent names (e.g. "researcher", "analyst", "writer")
- The last agent in the flow should NOT hand off — it should produce the final output

You are the meta-brain. The swarm agents are your hands. You direct, they execute,
you synthesize."""


outer_agent = Agent(
    model=_model,
    tools=[swarm],          # The only tool this agent needs
    system_prompt=OUTER_SYSTEM_PROMPT,
)


# ── Query ─────────────────────────────────────────────────────────────────────────
# A query that naturally decomposes into research → analysis → writing,
# which the outer agent will map onto a dynamically created swarm.

QUERY = (
    "Research, analyze, and summarize the key benefits and trade-offs of "
    "microservices architecture vs monolithic architecture for a startup "
    "building their first web application. Provide a clear recommendation."
)



def print_section(title: str) -> None:
    bar = "=" * 64
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")

if __name__ == "__main__":
    print_section("SWARM AS A TOOL — Dynamic Swarm Orchestration")
    print("  The outer agent will:")
    print("  1. Receive the query below")
    print("  2. Decide what specialized agents to create")
    print("  3. Call the `swarm` tool to run them")
    print("  4. Synthesize the swarm's output into a final answer")
    print()
    print(f"  Query: {QUERY}")
    print()
    print("  Watch stderr for debug logs showing the swarm being spun up.")
    print()

    logger.info("Starting outer agent...")

    # The outer agent handles everything from here:
    # - it will call the `swarm` tool with dynamically defined agents
    # - the swarm agents will hand off to each other
    # - the outer agent will read the SwarmResult and write the final answer
    result = outer_agent(QUERY)

    print_section("OUTER AGENT — FINAL ANSWER")
    print(str(result))
