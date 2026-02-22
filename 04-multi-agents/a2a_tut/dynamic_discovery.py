"""
Dynamic Agent Discovery — A2AClientToolProvider
================================================
Instead of manually wrapping each remote agent as a @tool,
A2AClientToolProvider fetches agent cards automatically and
injects ready-made tools into your local agent.

This pattern is useful when:
  - You don't know the agent's skills at coding time
  - You want to add/remove remote agents without code changes
  - You're building a marketplace or registry of agents

Requires the a2a_client extra:
  pip install 'strands-agents-tools[a2a_client]'

Run AFTER both servers are started:
  python server.py    # terminal 1
  python server2.py   # terminal 2
  python dynamic_discovery.py
"""

import logging
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

try:
    from strands_tools.a2a_client import A2AClientToolProvider
except ImportError:
    print(
        "\n[!] A2AClientToolProvider not installed.\n"
        "    Run: pip install 'strands-agents-tools[a2a_client]'\n"
    )
    raise SystemExit(1)

from strands import Agent

# ── Discover agents dynamically ────────────────────────────────────────────────
# Point at known server URLs. The provider fetches each /.well-known/agent.json,
# reads the skill list, and builds tool callables automatically.

provider = A2AClientToolProvider(
    known_agent_urls=[
        "http://127.0.0.1:9000",   # Calculator Agent
        "http://127.0.0.1:9001",   # Text Analyst Agent
    ]
)

print(f"\nDynamically discovered {len(provider.tools)} tool(s) from remote agents.")
print("These were injected automatically — no manual @tool wrappers needed.\n")

# ── Agent that uses dynamically discovered tools ───────────────────────────────

agent = Agent(
    name="Dynamic Orchestrator",
    system_prompt=(
        "You are a helpful assistant. "
        "You have access to tools that were auto-discovered from remote A2A agents. "
        "Use them to answer user questions. "
        "If asked to demonstrate, pick a tool and make a real call."
    ),
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    tools=provider.tools,
)

if __name__ == "__main__":
    queries = [
        # Let the agent discover and choose
        "What remote agents do you have access to? Pick one and make a sample call.",

        # Force it to use both
        "Ask the calculator agent what 256 / 16 is. "
        "Then ask the text agent how many words are in 'hello world this is a dynamic test'.",
    ]

    for q in queries:
        print(f"\n{'─' * 60}")
        print(f"Q: {q}")
        response = agent(q)
        print(f"A: {response}")
