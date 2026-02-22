"""
A2A Orchestrator — multi-agent pattern
=======================================
A LOCAL orchestrator LLM that uses THREE tools:
  - calculate    → remote Calculator Agent  (port 9000)
  - analyze_text → remote Text Analyst Agent (port 9001)
  - get_time     → local Python (no remote call)

The orchestrator decides which tool(s) to call for each query.
For compound questions it chains multiple tools together.

Run AFTER both servers are started:
  python server.py    # terminal 1
  python server2.py   # terminal 2
  python app.py       # terminal 3
"""

import logging
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from strands import Agent, tool
from strands.agent.a2a_agent import A2AAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ── Remote agent handles ───────────────────────────────────────────────────────
# Created once at import time — reused across all tool calls.

_calc_agent = A2AAgent(endpoint="http://127.0.0.1:9000", name="calculator")
_text_agent = A2AAgent(endpoint="http://127.0.0.1:9001", name="text_analyst")


def _extract(result) -> str:
    """Pull the text out of an AgentResult."""
    content = result.message.get("content", [])
    return content[0]["text"] if content else str(result.message)


# ── Tools ──────────────────────────────────────────────────────────────────────

@tool
def calculate(expression: str) -> str:
    """
    Perform a mathematical calculation.
    Delegates to the remote Calculator Agent via A2A.
    Use for any arithmetic, algebra, or numeric computation.
    """
    return _extract(_calc_agent(expression))


@tool
def analyze_text(text: str) -> str:
    """
    Analyze text for word count, character count, sentence count,
    longest word, and vowel count.
    Delegates to the remote Text Analyst Agent via A2A.
    """
    return _extract(_text_agent(text))


@tool
def get_current_time() -> str:
    """
    Return the current local date and time.
    This is a LOCAL tool — no remote agent call needed.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Orchestrator ───────────────────────────────────────────────────────────────

orchestrator = Agent(
    name="Orchestrator",
    system_prompt=(
        "You are a helpful assistant with access to three tools:\n"
        "  - calculate   : for any math or arithmetic (remote agent)\n"
        "  - analyze_text: for text statistics and word analysis (remote agent)\n"
        "  - get_current_time: for the current date/time (local)\n\n"
        "Always use the appropriate tool. "
        "For compound questions, chain multiple tools and combine their results."
    ),
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    tools=[calculate, analyze_text, get_current_time],
)


if __name__ == "__main__":
    questions = [
        # Routes to calculator agent only
        "What is 1234 * 5678?",

        # Routes to text analyst agent only
        "Analyze this: 'The quick brown fox jumps over the lazy dog'",

        # Local tool only — no remote call
        "What is the current time?",

        # Compound: needs both remote agents
        (
            "How many words are in 'To be or not to be that is the question'? "
            "And what is 17 * 48?"
        ),

        # Compound: needs calculator + time
        "If I invest $1000 at 5% annually for 10 years, what do I get? "
        "Also tell me the current timestamp.",
    ]

    for q in questions:
        print(f"\n{'─' * 60}")
        print(f"Q: {q}")
        response = orchestrator(q)
        print(f"A: {response}")
