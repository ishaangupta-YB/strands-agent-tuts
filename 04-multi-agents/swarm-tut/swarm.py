"""
swarm.py — Swarm multi-agent pattern demo
==========================================
A Swarm is a network of peer agents that autonomously hand off control to
each other. Unlike the orchestrator/tools pattern (one LLM routes to sub-agents),
in a Swarm ANY agent can transfer to ANY other agent via the handoff_to_agent
tool that the Swarm class injects automatically.

Architecture:
                   ┌──────────────┐
              ┌───>│  researcher  │<───┐
              │    └──────┬───────┘    │
              │           │            │
              │    ┌──────▼───────┐    │
              │    │  architect   │<───┤
              │    └──────┬───────┘    │
              │           │            │
              │    ┌──────▼───────┐    │
              │    │    coder     │────┤
              │    └──────┬───────┘    │
              │           │            │
              └───────────│──────┌─────▼──────┐
                          └─────>│  reviewer  │
                                 └────────────┘

Each arrow represents a possible handoff_to_agent call. The Swarm class
tracks history, enforces limits, and detects ping-pong loops.

Run:
  python 04-multi-agents/swarm-tut/swarm.py
"""

import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Enable multiagent debug logs so handoffs are visible in real time
logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

from strands.multiagent import Swarm
from agents import researcher, architect, coder, reviewer


# ── Build the Swarm ─────────────────────────────────────────────────────────────
# Parameters:
#   entry_point  — first agent to receive the task (researcher starts)
#   max_handoffs — hard cap on agent-to-agent transfers
#   max_iterations — hard cap on total LLM calls across all agents
#   execution_timeout — wall-clock time limit for the whole run (seconds)
#   node_timeout — per-agent time limit per turn (seconds)
#   repetitive_handoff_detection_window — look-back window to detect A→B→A→B loops
#   repetitive_handoff_min_unique_agents — min distinct agents in the window to
#                                          avoid being flagged as repetitive

swarm = Swarm(
    [researcher, architect, coder, reviewer],
    entry_point=researcher,
    max_handoffs=20,
    max_iterations=20,
    execution_timeout=900.0,        # 15 minutes total
    node_timeout=300.0,             # 5 minutes per agent turn
    repetitive_handoff_detection_window=8,
    repetitive_handoff_min_unique_agents=3,
)


# ── Sample task ─────────────────────────────────────────────────────────────────
# A concrete, well-scoped engineering task that exercises all four agents:
#   researcher  → clarify scope, list requirements
#   architect   → design endpoints and data model
#   coder       → write FastAPI implementation
#   reviewer    → approve or request changes

TASK = (
    "Design and implement a Python REST API for a todo app. "
    "The API should support: creating todos, listing all todos, getting a single "
    "todo by ID, updating a todo (title and/or completion status), and deleting a "
    "todo. Use FastAPI with an in-memory dict store (no database needed). "
    "Deliver the implementation as a single runnable Python file."
)


# ── Display helpers ─────────────────────────────────────────────────────────────

def print_section(title: str) -> None:
    bar = "=" * 64
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")


def display_results(result) -> None:
    """
    Demonstrate every field on SwarmResult.

    SwarmResult fields:
      result.status            — overall outcome (Status.COMPLETED, FAILED, etc.)
      result.execution_count   — total LLM calls made across ALL agents
      result.execution_time    — wall-clock seconds (note: SDK returns ms label but value is seconds)
      result.node_history      — ordered list of SwarmNode objects that ran (.node_id = agent name)
      result.results           — dict[agent_name -> NodeResult]; last output per agent
      result.accumulated_usage — aggregated token counts across all agents
    """

    print_section("SWARM RESULT — FIELD BY FIELD")

    # ── 1. Status ────────────────────────────────────────────────────────────────
    # Possible values: Status.COMPLETED, Status.FAILED, Status.MAX_HANDOFFS_REACHED,
    #                  Status.TIMEOUT, Status.REPETITIVE_HANDOFFS_DETECTED
    print(f"  result.status          : {result.status}")

    # ── 2. Performance metrics ───────────────────────────────────────────────────
    print(f"  result.execution_count : {result.execution_count}  (total LLM calls across all agents)")
    print(f"  result.execution_time  : {result.execution_time:.1f}s")

    # ── 3. Token usage ───────────────────────────────────────────────────────────
    # accumulated_usage aggregates inputTokens + outputTokens from every agent turn
    print(f"  result.accumulated_usage: {result.accumulated_usage}")
    print()

    # ── 4. node_history — who ran and in what order ──────────────────────────────
    # Each entry is a SwarmNode; .node_id is the agent's name string.
    # An agent can appear multiple times if it was handed back to (e.g. coder after review).
    print_section("NODE HISTORY  (result.node_history)")
    for i, node in enumerate(result.node_history):
        print(f"  [{i + 1}] Agent: {node.node_id}")
    print()
    path = " → ".join(node.node_id for node in result.node_history)
    print(f"  Full path : {path}")
    print(f"  Handoffs  : {len(result.node_history) - 1}")

    # ── 5. Per-agent results — access a specific agent's last output ─────────────
    # result.results is a dict keyed by agent name string.
    # Each value is a NodeResult; .result is the AgentResult from that agent's last turn.
    # Use this to pull the output from a specific agent by name.
    print_section("PER-AGENT RESULTS  (result.results[name].result)")
    for agent_name in result.results:
        node_result = result.results[agent_name]          # NodeResult object
        agent_output = node_result.result                 # AgentResult (the actual LLM response)
        text = str(agent_output)
        preview = text[:400] + "\n  ...(truncated)" if len(text) > 400 else text
        print(f"  [{agent_name.upper()}]")
        print(f"  {preview}")
        print()

    # ── 6. Final output — the last agent's complete response ─────────────────────
    # str(result) returns the text from the final agent that ended the swarm.
    print_section("FINAL OUTPUT  (str(result))")
    print(str(result))


if __name__ == "__main__":
    print_section("SWARM: REST API Design + Implementation")
    print(f"  Task: {TASK}")
    print()
    print("  Agents  : researcher → architect → coder → reviewer")
    print("  Entry   : researcher")
    print()
    print("  Watch stderr for agent handoff events (DEBUG logs).")
    print("  Each agent's streaming output appears below as it runs.")
    print()

    logger.info("Starting swarm execution...")
    result = swarm(TASK)
    display_results(result)
