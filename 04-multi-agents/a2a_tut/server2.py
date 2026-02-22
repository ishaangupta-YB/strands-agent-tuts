"""
A2A Server 2 — Text Analyst Agent  (port 9001)
===============================================
A second specialized remote agent with custom @tool functions.
Demonstrates that an A2A ecosystem can have many independent agents,
each with different skills, all reachable via the same protocol.

Run: python server2.py
"""

import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import uvicorn
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Custom tools for this agent ────────────────────────────────────────────────

@tool
def word_count(text: str) -> str:
    """Count the number of words in the given text."""
    return f"{len(text.split())} words"


@tool
def text_stats(text: str) -> str:
    """Return word count, character count, and sentence count for the given text."""
    words = len(text.split())
    chars = len(text)
    sentences = sum(text.count(p) for p in ".!?")
    return f"Words: {words} | Characters: {chars} | Sentences: {sentences}"


@tool
def find_longest_word(text: str) -> str:
    """Find the longest word in the given text."""
    words = [w.strip(".,!?;:\"'") for w in text.split() if w.strip(".,!?;:\"'")]
    if not words:
        return "No words found."
    longest = max(words, key=len)
    return f"Longest word: '{longest}' ({len(longest)} characters)"


@tool
def count_vowels(text: str) -> str:
    """Count the number of vowels (a, e, i, o, u) in the given text."""
    count = sum(1 for c in text.lower() if c in "aeiou")
    return f"{count} vowels"


# ── Agent + A2A server ─────────────────────────────────────────────────────────

agent = Agent(
    name="Text Analyst",
    description=(
        "Analyzes text: counts words, computes statistics, "
        "finds the longest word, and counts vowels."
    ),
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    tools=[word_count, text_stats, find_longest_word, count_vowels],
    callback_handler=None,
)

a2a_server = A2AServer(
    agent=agent,
    host="127.0.0.1",
    port=9001,
)


@asynccontextmanager
async def lifespan(app):
    logger.info("Text Analyst A2A server STARTED on http://127.0.0.1:9001")
    logger.info("  Agent card : http://127.0.0.1:9001/.well-known/agent.json")
    logger.info("  Invoke     : POST http://127.0.0.1:9001/")
    yield
    logger.info("Text Analyst A2A server STOPPED.")


fastapi_app = a2a_server.to_fastapi_app(app_kwargs={"lifespan": lifespan})

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="127.0.0.1", port=9001)
